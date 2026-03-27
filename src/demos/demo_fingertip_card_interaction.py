import cv2
import argparse
import time
import numpy as np
from collections import deque
import math
from cvzone.HandTrackingModule import HandDetector

# Import reusable components from util.py
from asimov.util import OneEuroFilter, get_centroid

# --- APPLICATION CONSTANTS (Shared) ---
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS_SMOOTHING_ALPHA = 0.1

# Card Detection and Filtering
RECT_MIN_AREA_PERCENT = 0.005
RECT_MAX_AREA_PERCENT = 0.5
ASPECT_RATIO_MIN = 0.6
ASPECT_RATIO_MAX = 1.5
APPROX_POLY_EPSILON_FACTOR = 0.03

# Tracking and Smoothing
CARD_EXPIRATION_SECONDS = 3.0
QUEUE_MAX_SIZE = 10
FILTER_MIN_CUTOFF_CARD = 1.0
FILTER_BETA_CARD = 0.08

# Finger Tracking & Smoothing
FILTER_MIN_CUTOFF_FINGER = 0.5  # More aggressive smoothing for jittery hand tracking
FILTER_BETA_FINGER = 0.01
FINGER_RADIUS = 10  # Size of the yellow circle
FINGER_LANDMARK_ID = 8  # Index finger tip landmark ID (MediaPipe)

# Drawing Colors
CONTOUR_COLOR_DEFAULT = (255, 0, 0)  # Blue border
CONTOUR_COLOR_COLLISION = (0, 255, 0)  # Green border
FINGER_COLOR = (0, 255, 255)  # Yellow finger tip (B, G, R)
INFO_BG_COLOR = (0, 0, 0)
INFO_TEXT_COLOR = (255, 255, 255)
INFO_FONT = cv2.FONT_HERSHEY_SIMPLEX
INFO_FONT_SCALE = 0.7
CONTOUR_THICKNESS = 4

# --- CVZONE HAND DETECTOR SETUP ---
detector = HandDetector(detectionCon=0.7, maxHands=1)

# --- GLOBAL STATE ---
# Card Queue (similar structure to stabilized demo)
# rect = { 'filters': {'x0': OneEuroFilter, 'y0': OneEuroFilter, ...}, 'pts_smooth': np.array(...), 'timestamp': time.time() }
rect_queue = deque(maxlen=QUEUE_MAX_SIZE)

# Finger Tip Filters (OneEuroFilter is imported from util.py)
finger_x_filter = None
finger_y_filter = None
is_finger_tracking_active = False


# --- UTILITY FUNCTIONS ---


def setup_detector_and_args():
    """Initializes the argument parser and video capture settings."""
    parser = argparse.ArgumentParser(
        description="Real-time Card Interaction Demo (Finger Tip Collision)."
    )
    parser.add_argument(
        "--device", type=int, default=0, help="Camera device index to use (default: 0)."
    )
    args = parser.parse_args()
    return args.device


def initialize_filters(fps_estimate):
    """Initializes the global OneEuroFilters for the finger tip."""
    global finger_x_filter, finger_y_filter

    # Initialize the finger filters using the imported OneEuroFilter
    finger_x_filter = OneEuroFilter(
        freq=fps_estimate,
        min_cutoff=FILTER_MIN_CUTOFF_FINGER,
        beta=FILTER_BETA_FINGER,
        init=FRAME_WIDTH / 2,
    )
    finger_y_filter = OneEuroFilter(
        freq=fps_estimate,
        min_cutoff=FILTER_MIN_CUTOFF_FINGER,
        beta=FILTER_BETA_FINGER,
        init=FRAME_HEIGHT / 2,
    )


def process_frame_for_rectangles(frame):
    """
    Detects and filters potential card-like rectangles in the frame.
    Returns a list of the 4-point corners for each detected rectangle.
    """
    h, w, _ = frame.shape

    # 1. Preprocessing: Convert to grayscale and apply Gaussian blur
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Edge Detection: Use Canny
    edges = cv2.Canny(blur, 50, 150)

    # 3. Find Contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_rectangles = []
    min_area = w * h * RECT_MIN_AREA_PERCENT
    max_area = w * h * RECT_MAX_AREA_PERCENT

    for contour in contours:
        area = cv2.contourArea(contour)

        # 4. Basic Area Filtering
        if area < min_area or area > max_area:
            continue

        # 5. Approximate Contour to a Polygon
        perimeter = cv2.arcLength(contour, True)
        epsilon = perimeter * APPROX_POLY_EPSILON_FACTOR
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # 6. Rectangle Specific Filtering
        if len(approx) == 4:
            x, y, cw, ch = cv2.boundingRect(approx)
            aspect_ratio = cw / ch

            if ASPECT_RATIO_MIN <= aspect_ratio <= ASPECT_RATIO_MAX:
                detected_rectangles.append(approx.reshape(4, 2))

    return detected_rectangles


def match_and_update_queue(detected_rectangles, fps_estimate):
    """
    Matches detected rectangles to existing tracked rectangles in the queue
    and applies One Euro filtering to all 4 corner coordinates.
    """
    current_time = time.time()
    matched_indices = [False] * len(rect_queue)
    MATCH_DISTANCE_THRESHOLD = 50

    for new_rect_pts in detected_rectangles:
        # Uses the imported get_centroid
        new_cx, new_cy = get_centroid(new_rect_pts)
        best_match_index = -1
        min_distance = float("inf")

        for i, tracked_rect in enumerate(rect_queue):
            tracked_cx_prev = tracked_rect["filters"]["x0"].x_prev
            tracked_cy_prev = tracked_rect["filters"]["y0"].x_prev
            dist = math.sqrt(
                (tracked_cx_prev - new_cx) ** 2 + (tracked_cy_prev - new_cy) ** 2
            )

            if (
                dist < min_distance
                and dist < MATCH_DISTANCE_THRESHOLD
                and not matched_indices[i]
            ):
                min_distance = dist
                best_match_index = i

        if best_match_index != -1:
            tracked_rect = rect_queue[best_match_index]

            current_tracked_points = np.array(
                [
                    [
                        tracked_rect["filters"][f"x{j}"].x_prev,
                        tracked_rect["filters"][f"y{j}"].x_prev,
                    ]
                    for j in range(4)
                ]
            )

            pts_smooth = np.zeros((4, 2), dtype=np.int32)

            for j in range(4):
                fx_prev, fy_prev = current_tracked_points[j]
                min_dist_corner = float("inf")
                best_new_point_index = -1

                for k in range(4):
                    new_x, new_y = new_rect_pts[k]
                    dist = math.sqrt((fx_prev - new_x) ** 2 + (fy_prev - new_y) ** 2)

                    if dist < min_dist_corner:
                        min_dist_corner = dist
                        best_new_point_index = k

                if best_new_point_index != -1:
                    matched_new_x, matched_new_y = new_rect_pts[best_new_point_index]

                    # Apply imported One Euro Filter for cards
                    pts_smooth[j, 0] = int(
                        tracked_rect["filters"][f"x{j}"].update(matched_new_x)
                    )
                    pts_smooth[j, 1] = int(
                        tracked_rect["filters"][f"y{j}"].update(matched_new_y)
                    )

            tracked_rect["pts_smooth"] = pts_smooth
            tracked_rect["timestamp"] = current_time
            matched_indices[best_match_index] = True

        else:
            # New detection: Create a new tracked rectangle with filters initialized
            new_filters = {}
            for i in range(4):
                # Uses the imported OneEuroFilter
                new_filters[f"x{i}"] = OneEuroFilter(
                    freq=fps_estimate,
                    min_cutoff=FILTER_MIN_CUTOFF_CARD,
                    beta=FILTER_BETA_CARD,
                    init=new_rect_pts[i, 0],
                )
                new_filters[f"y{i}"] = OneEuroFilter(
                    freq=fps_estimate,
                    min_cutoff=FILTER_MIN_CUTOFF_CARD,
                    beta=FILTER_BETA_CARD,
                    init=new_rect_pts[i, 1],
                )

            new_tracked_rect = {
                "filters": new_filters,
                "pts_smooth": new_rect_pts.astype(np.int32),
                "timestamp": current_time,
            }
            rect_queue.append(new_tracked_rect)

    # --- Step 2: Expire Old Rects ---
    new_rect_queue_list = []
    for tracked_rect in rect_queue:
        if (current_time - tracked_rect["timestamp"]) < CARD_EXPIRATION_SECONDS:
            new_rect_queue_list.append(tracked_rect)

    rect_queue.clear()
    rect_queue.extend(new_rect_queue_list)


def get_finger_tip_position(frame):
    """
    Uses cvzone HandDetector to detect the index finger tip and smooth its position.

    Returns: (x, y) coordinates of the smoothed index finger tip, or None.
    """
    global is_finger_tracking_active

    hands, frame = detector.findHands(frame, draw=False)

    if hands:
        hand = hands[0]
        lmList = hand["lmList"]

        tip_lm = lmList[FINGER_LANDMARK_ID]

        raw_x = tip_lm[0]
        raw_y = tip_lm[1]

        smoothed_x = finger_x_filter.update(raw_x)
        smoothed_y = finger_y_filter.update(raw_y)

        is_finger_tracking_active = True
        return (int(smoothed_x), int(smoothed_y))
    else:
        is_finger_tracking_active = False
        return None


def check_collision_and_draw(frame, finger_tip_pos):
    """
    Checks if the finger tip is inside any of the tracked rectangles and draws them.

    Args:
        frame (np.ndarray): The current video frame.
        finger_tip_pos (tuple | None): (x, y) coordinates of the smoothed finger tip.
    """

    collision_detected = False

    # 1. Draw the tracked rectangles (smoothed)
    for tracked_rect in rect_queue:
        # Get the smoothed 4 corner points
        pts = tracked_rect["pts_smooth"].reshape((-1, 1, 2))

        # Check for collision if the finger tip is visible
        is_touching = False
        if finger_tip_pos is not None:
            # Check if point is inside the polygon (rectangle)
            # result >= 0 means inside or on the edge
            result = cv2.pointPolygonTest(pts, finger_tip_pos, measureDist=False)

            if result >= 0:
                is_touching = True
                collision_detected = True  # Mark that at least one collision occurred

        # Determine color: Green if touching, Blue otherwise
        color = CONTOUR_COLOR_COLLISION if is_touching else CONTOUR_COLOR_DEFAULT

        # Draw the rectangle border
        cv2.polylines(
            frame, [pts], isClosed=True, color=color, thickness=CONTOUR_THICKNESS
        )

        # Draw centroid (optional)
        smooth_cx, smooth_cy = get_centroid(tracked_rect["pts_smooth"])
        cv2.circle(frame, (int(smooth_cx), int(smooth_cy)), 5, color, -1)

    # 2. Draw the finger tip (smoothed)
    if finger_tip_pos is not None:
        cv2.circle(frame, finger_tip_pos, FINGER_RADIUS, FINGER_COLOR, -1)

    return collision_detected


def draw_info_box(frame, text, x, y):
    """Draws a text label with a solid background for readability."""
    (text_w, text_h), baseline = cv2.getTextSize(text, INFO_FONT, INFO_FONT_SCALE, 2)
    cv2.rectangle(
        frame,
        (x, y - text_h - baseline - 5),
        (x + text_w + 10, y + 5),
        INFO_BG_COLOR,
        -1,
    )
    cv2.putText(
        frame,
        text,
        (x + 5, y - baseline),
        INFO_FONT,
        INFO_FONT_SCALE,
        INFO_TEXT_COLOR,
        2,
        cv2.LINE_AA,
    )


def main():
    """Main function to run the video processing loop."""

    device_index = setup_detector_and_args()

    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    fps_estimate = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Initialize all filters
    initialize_filters(fps_estimate)

    # FPS tracking variables
    pTime = 0
    avg_fps = 0.0

    print(
        f"Starting card interaction demo on device {device_index}. Expected FPS: {fps_estimate:.1f}"
    )

    while True:
        success, img = cap.read()
        if not success:
            print(
                f"Error: Could not read from video device index {device_index}. Exiting."
            )
            break

        # Calculate FPS
        cTime = time.time()
        inst_fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime

        # Apply EMA smoothing for stable display
        if avg_fps == 0.0:
            avg_fps = inst_fps
        else:
            avg_fps = (FPS_SMOOTHING_ALPHA * inst_fps) + (
                (1 - FPS_SMOOTHING_ALPHA) * avg_fps
            )

        # Flip the frame for a mirror effect (more intuitive)
        img = cv2.flip(img, 1)

        # 1. Detect candidate rectangles (Cards)
        detected_rectangles = process_frame_for_rectangles(img)

        # 2. Match, Update, and Filter Card Queue
        match_and_update_queue(detected_rectangles, fps_estimate)

        # 3. Detect and Filter Finger Tip
        finger_tip_pos = get_finger_tip_position(img)

        # 4. Check Collision and Draw (Cards and Finger)
        collision_detected = check_collision_and_draw(img, finger_tip_pos)

        # 5. Display Information
        collision_text = "TOUCHING" if collision_detected else "Tracking"
        finger_status = "ACTIVE" if is_finger_tracking_active else "LOST"

        status_text = f"Cards: {len(rect_queue)} | Finger: {finger_status} | Collision: {collision_text} | FPS: {int(avg_fps)}"
        draw_info_box(img, status_text, 10, FRAME_HEIGHT - 10)

        cv2.imshow("Finger-Card Interaction Demo", img)

        # Check for 'q' or ESC (key code 27) to quit
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Demo terminated.")


if __name__ == "__main__":
    main()
