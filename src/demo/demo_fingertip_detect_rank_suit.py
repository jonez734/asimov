import cv2
import argparse
import time
import numpy as np
from collections import deque
import math
import mediapipe as mp

# Import reusable components from util.py (corrected to use asimov.util)
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
APPROX_POLY_EPSILON_FACTOR = 0.02 

# Card Identification Constants (Target size for the perspective warp/crop)
CARD_TARGET_WIDTH = 100
CARD_TARGET_HEIGHT = 140

# Tracking and Smoothing
CARD_EXPIRATION_SECONDS = 1.5 
QUEUE_MAX_SIZE = 100 
FILTER_MIN_CUTOFF_CARD = 1.0
FILTER_BETA_CARD = 0.08
GROUPING_IOU_THRESHOLD = 0.6 

# Finger Tracking & Smoothing
FILTER_MIN_CUTOFF_FINGER = 0.5 
FILTER_BETA_FINGER = 0.01 
FINGER_RADIUS = 10 
FINGER_LANDMARK_ID = 8 

# Drawing Colors
CONTOUR_COLOR_DEFAULT = (255, 0, 0) # Blue border
CONTOUR_COLOR_COLLISION = (0, 255, 0) # Green border
FINGER_COLOR = (0, 255, 255) # Yellow finger tip (B, G, R)
INFO_BG_COLOR = (0, 0, 0)
INFO_TEXT_COLOR = (255, 255, 255)
CARD_TEXT_COLOR = (255, 255, 255)
INFO_FONT = cv2.FONT_HERSHEY_SIMPLEX
INFO_FONT_SCALE = 0.7
CARD_FONT_SCALE = 0.5
CONTOUR_THICKNESS = 4

# --- MEDIAPIPE SETUP ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# --- GLOBAL STATE ---
# rect = { 
#   'filters': {...}, 
#   'pts_smooth': np.array(...), 
#   'timestamp': time.time(), 
#   'card_id': int, 
#   'card_name': str 
# }
rect_queue = deque(maxlen=QUEUE_MAX_SIZE)
finger_x_filter = None
finger_y_filter = None
is_finger_tracking_active = False
card_id_counter = 0 # Unique ID generator for new cards

# --- UTILITY FUNCTIONS ---

def get_bounding_box(pts):
    """Calculates the bounding box (x_min, y_min, x_max, y_max) from a set of points."""
    x, y, w, h = cv2.boundingRect(pts)
    return (x, y, x + w, y + h) 

def calculate_iou(boxA, boxB):
    """Calculates Intersection over Union (IoU) of two bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h

    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = inter_area / float(areaA + areaB - inter_area)
    return iou

def group_similar_rectangles(detected_rectangles, iou_threshold):
    """
    Groups highly overlapping rectangles (NMS) and keeps only the largest one.
    """
    if not detected_rectangles:
        return []
        
    boxes = [get_bounding_box(rect) for rect in detected_rectangles]
    areas = [(box[2] - box[0]) * (box[3] - box[1]) for box in boxes]
    indices = np.argsort(areas)[::-1]
    
    keep = []
    
    while len(indices) > 0:
        i = indices[0]
        keep.append(i)
        
        other_indices = indices[1:]
        suppress = []
        for j in other_indices:
            iou = calculate_iou(boxes[i], boxes[j])
            if iou > iou_threshold:
                suppress.append(j)
        
        indices = [idx for idx in other_indices if idx not in suppress]

    return [detected_rectangles[i] for i in keep]

def setup_detector_and_args():
    """Initializes the argument parser and video capture settings."""
    parser = argparse.ArgumentParser(description="Card Tracking and Identification Demo (Perspective Warp).")
    parser.add_argument("--device", type=int, default=0, help="Camera device index to use (default: 0).")
    args = parser.parse_args()
    return args.device

def initialize_filters(fps_estimate):
    """Initializes the global OneEuroFilters for the finger tip."""
    global finger_x_filter, finger_y_filter
    
    finger_x_filter = OneEuroFilter(
        freq=fps_estimate, 
        min_cutoff=FILTER_MIN_CUTOFF_FINGER, 
        beta=FILTER_BETA_FINGER, 
        init=FRAME_WIDTH / 2
    )
    finger_y_filter = OneEuroFilter(
        freq=fps_estimate, 
        min_cutoff=FILTER_MIN_CUTOFF_FINGER, 
        beta=FILTER_BETA_FINGER, 
        init=FRAME_HEIGHT / 2
    )

def process_frame_for_rectangles(frame):
    """
    Detects and filters potential card-like rectangles, using RETR_LIST for overlapping cards.
    """
    h, w, _ = frame.shape
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150) 
    
    # Use RETR_LIST to find all contours, including internal ones (for overlapping cards)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    detected_rectangles = []
    min_area = w * h * RECT_MIN_AREA_PERCENT
    max_area = w * h * RECT_MAX_AREA_PERCENT

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < min_area or area > max_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        epsilon = perimeter * APPROX_POLY_EPSILON_FACTOR
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            x, y, cw, ch = cv2.boundingRect(approx)
            aspect_ratio = cw / ch
            
            if ASPECT_RATIO_MIN <= aspect_ratio <= ASPECT_RATIO_MAX:
                detected_rectangles.append(approx.reshape(4, 2))

    return detected_rectangles

def match_and_update_queue(detected_rectangles, fps_estimate):
    """
    Matches detected rectangles to existing tracked rectangles and updates filters.
    Assigns unique IDs to new detections.
    """
    global card_id_counter
    current_time = time.time()
    matched_indices = [False] * len(rect_queue)
    MATCH_DISTANCE_THRESHOLD = 50 

    for new_rect_pts in detected_rectangles:
        new_cx, new_cy = get_centroid(new_rect_pts)
        best_match_index = -1
        min_distance = float('inf')

        for i, tracked_rect in enumerate(rect_queue):
            tracked_cx_prev = tracked_rect['filters']['x0'].x_prev 
            tracked_cy_prev = tracked_rect['filters']['y0'].x_prev
            dist = math.sqrt((tracked_cx_prev - new_cx)**2 + (tracked_cy_prev - new_cy)**2)
            
            if dist < min_distance and dist < MATCH_DISTANCE_THRESHOLD and not matched_indices[i]:
                min_distance = dist
                best_match_index = i

        if best_match_index != -1:
            # --- MATCH FOUND: Update filters and timestamp ---
            tracked_rect = rect_queue[best_match_index]
            
            current_tracked_points = np.array([
                [tracked_rect['filters'][f'x{j}'].x_prev, tracked_rect['filters'][f'y{j}'].x_prev] 
                for j in range(4)
            ])
            
            pts_smooth = np.zeros((4, 2), dtype=np.int32)
            
            for j in range(4): 
                fx_prev, fy_prev = current_tracked_points[j]
                min_dist_corner = float('inf')
                best_new_point_index = -1
                
                for k in range(4):
                    new_x, new_y = new_rect_pts[k]
                    dist = math.sqrt((fx_prev - new_x)**2 + (fy_prev - new_y)**2)
                    
                    if dist < min_dist_corner:
                        min_dist_corner = dist
                        best_new_point_index = k
                
                if best_new_point_index != -1:
                    matched_new_x, matched_new_y = new_rect_pts[best_new_point_index]
                    
                    pts_smooth[j, 0] = int(tracked_rect['filters'][f'x{j}'].update(matched_new_x))
                    pts_smooth[j, 1] = int(tracked_rect['filters'][f'y{j}'].update(matched_new_y))
            
            tracked_rect['pts_smooth'] = pts_smooth
            tracked_rect['timestamp'] = current_time
            matched_indices[best_match_index] = True

        else:
            # --- NO MATCH FOUND: New detection, initialize filters and assign ID ---
            new_filters = {}
            for i in range(4):
                new_filters[f'x{i}'] = OneEuroFilter(freq=fps_estimate, min_cutoff=FILTER_MIN_CUTOFF_CARD, beta=FILTER_BETA_CARD, init=new_rect_pts[i, 0])
                new_filters[f'y{i}'] = OneEuroFilter(freq=fps_estimate, min_cutoff=FILTER_MIN_CUTOFF_CARD, beta=FILTER_BETA_CARD, init=new_rect_pts[i, 1])
            
            card_id_counter += 1
            new_tracked_rect = {
                'filters': new_filters,
                'pts_smooth': new_rect_pts.astype(np.int32), 
                'timestamp': current_time,
                'card_id': card_id_counter,
                'card_name': f"Card #{card_id_counter}", # Initial placeholder name
            }
            rect_queue.append(new_tracked_rect)

    # --- Expire Old Rects ---
    new_rect_queue_list = []
    for tracked_rect in rect_queue:
        if (current_time - tracked_rect['timestamp']) < CARD_EXPIRATION_SECONDS:
            new_rect_queue_list.append(tracked_rect)
            
    rect_queue.clear()
    rect_queue.extend(new_rect_queue_list)

def get_card_image(frame, pts_smooth):
    """
    Performs a perspective transformation to get a frontal, fixed-size image of the card.
    
    This function implements the "identify based on only a detected rectangle" core idea.
    
    
    
    Args:
        frame (np.ndarray): The original video frame.
        pts_smooth (np.ndarray): The 4 smoothed corner points (4, 2).
        
    Returns:
        np.ndarray: The cropped and warped card image.
    """
    pts = pts_smooth.astype(np.float32)
    
    # 1. Order the detected points consistently: TL, TR, BR, BL
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # Top-left (smallest sum x+y)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    # Bottom-right (largest sum x+y)
    rect[2] = pts[np.argmax(s)]
    
    # Top-right (smallest difference y-x)
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    # Bottom-left (largest difference y-x)
    rect[3] = pts[np.argmax(diff)]
    
    # 2. Define destination points (a perfect rectangle of fixed size)
    dst_pts = np.array([
        [0, 0],
        [CARD_TARGET_WIDTH - 1, 0],
        [CARD_TARGET_WIDTH - 1, CARD_TARGET_HEIGHT - 1],
        [0, CARD_TARGET_HEIGHT - 1]
    ], dtype=np.float32)

    # 3. Get the perspective transformation matrix (M)
    M = cv2.getPerspectiveTransform(rect, dst_pts)
    
    # 4. Apply the transformation to the frame
    warped = cv2.warpPerspective(frame, M, (CARD_TARGET_WIDTH, CARD_TARGET_HEIGHT))
    
    return warped

def identify_card(card_image, card_id):
    """
    (Placeholder) Simulates card identification by processing the cropped image.
    
    In a real application, this is where cv2.matchTemplate or a more advanced 
    classification model would run against the `card_image`.
    
    Args:
        card_image (np.ndarray): The fixed-size, frontal view of the card.
        card_id (int): The unique ID of the tracked card.
        
    Returns:
        str: The identified card name (e.g., "Ace of Spades").
    """
    # Placeholder: Run a simple process to prove the image is being used
    
    # Convert to grayscale and apply Canny edges just for visualization/complexity
    gray = cv2.cvtColor(card_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # The actual identification logic goes here (e.g., template matching the rank/suit pips)
    
    return f"Card #{card_id} (Processed)"

def get_finger_tip_position(frame):
    """
    Uses MediaPipe Hands to detect the index finger tip and smooth its position.
    """
    global is_finger_tracking_active
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)
    
    h, w, _ = frame.shape
    
    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        tip_lm = hand_landmarks.landmark[FINGER_LANDMARK_ID]
        
        raw_x = tip_lm.x * w
        raw_y = tip_lm.y * h
        
        smoothed_x = finger_x_filter.update(raw_x)
        smoothed_y = finger_y_filter.update(raw_y)
        
        is_finger_tracking_active = True
        return (int(smoothed_x), int(smoothed_y))
    else:
        is_finger_tracking_active = False
        return None

def check_collision_and_draw(frame, finger_tip_pos, current_time):
    """
    Checks collision, identifies the card, and draws contours and names.
    
    Returns: (collision_detected, warped_card_image)
    """
    collision_detected = False
    warped_card_image = None
    
    # 1. Draw and Process the tracked rectangles
    for i, tracked_rect in enumerate(rect_queue):
        pts = tracked_rect['pts_smooth'].reshape((-1, 1, 2))
        
        # --- CARD IDENTIFICATION STEP ---
        try:
            # Get the isolated, frontal card image
            current_warped = get_card_image(frame, tracked_rect['pts_smooth'])
            # Run identification on the isolated image
            tracked_rect['card_name'] = identify_card(current_warped, tracked_rect['card_id'])
            
            # Use the first tracked card's warped image for the separate viewer
            if i == 0:
                warped_card_image = current_warped
                
        except Exception:
            # Handle cases where perspective warp fails (e.g., points too distorted)
            tracked_rect['card_name'] = f"ID #{tracked_rect['card_id']} (Warp Error)"
            pass

        # --- COLLISION CHECK ---
        is_touching = False
        if finger_tip_pos is not None:
            result = cv2.pointPolygonTest(pts, finger_tip_pos, measureDist=False)
            
            if result >= 0:
                is_touching = True
                collision_detected = True 
                tracked_rect['timestamp'] = current_time # Reset Expiration Timer
                
        # --- DRAWING ---
        color = CONTOUR_COLOR_COLLISION if is_touching else CONTOUR_COLOR_DEFAULT
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=CONTOUR_THICKNESS)
        
        # Draw Card Name
        x_min = pts.min(axis=0)[0][0]
        y_min = pts.min(axis=0)[0][1]
        cv2.putText(frame, tracked_rect['card_name'], (x_min, y_min - 10), 
                    INFO_FONT, CARD_FONT_SCALE, CARD_TEXT_COLOR, 2, cv2.LINE_AA)
        
        # Draw centroid (optional)
        smooth_cx, smooth_cy = get_centroid(tracked_rect['pts_smooth'])
        cv2.circle(frame, (int(smooth_cx), int(smooth_cy)), 5, color, -1)

    # 2. Draw the finger tip (smoothed)
    if finger_tip_pos is not None:
        cv2.circle(frame, finger_tip_pos, FINGER_RADIUS, FINGER_COLOR, -1)
        
    return collision_detected, warped_card_image


def draw_info_box(frame, text, x, y):
    """Draws a text label with a solid background for readability."""
    (text_w, text_h), baseline = cv2.getTextSize(text, INFO_FONT, INFO_FONT_SCALE, 2)
    cv2.rectangle(frame, (x, y - text_h - baseline - 5), (x + text_w + 10, y + 5), INFO_BG_COLOR, -1)
    cv2.putText(frame, text, (x + 5, y - baseline), INFO_FONT, INFO_FONT_SCALE, INFO_TEXT_COLOR, 2, cv2.LINE_AA)


def main():
    """Main function to run the video processing loop."""
    
    device_index = setup_detector_and_args()

    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    fps_estimate = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    initialize_filters(fps_estimate) 

    # FPS tracking variables
    pTime = 0
    avg_fps = 0.0
    
    print(f"Starting card identification demo on device {device_index}. Expected FPS: {fps_estimate:.1f}")
    
    while True:
        success, img = cap.read()
        if not success:
            print(f"Error: Could not read from video device index {device_index}. Exiting.")
            break
        
        cTime = time.time()
        inst_fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        
        if avg_fps == 0.0:
            avg_fps = inst_fps
        else:
            avg_fps = (FPS_SMOOTHING_ALPHA * inst_fps) + ((1 - FPS_SMOOTHING_ALPHA) * avg_fps)
            
        img = cv2.flip(img, 1)

        # 1. Detect candidate rectangles
        detected_rectangles = process_frame_for_rectangles(img)

        # 1.5. Group similar, overlapping rectangles (NMS)
        detected_rectangles = group_similar_rectangles(detected_rectangles, GROUPING_IOU_THRESHOLD)
        
        # 2. Match, Update, and Filter Card Queue
        match_and_update_queue(detected_rectangles, fps_estimate)
        
        # 3. Detect and Filter Finger Tip
        finger_tip_pos = get_finger_tip_position(img)

        # 4. Check Collision, Identify Card, and Draw
        collision_detected, warped_card_image = check_collision_and_draw(img, finger_tip_pos, cTime)
        
        # 5. Display Warped Card View (Visual confirmation that card isolation works)
        if warped_card_image is not None:
            cv2.imshow("Warped Card View", warped_card_image)
        
        # 6. Display Information
        collision_text = "TOUCHING" if collision_detected else "Tracking"
        finger_status = "ACTIVE" if is_finger_tracking_active else "LOST"
        
        status_text = f"Cards: {len(rect_queue)} | Finger: {finger_status} | Collision: {collision_text} | FPS: {int(avg_fps)}"
        draw_info_box(img, status_text, 10, FRAME_HEIGHT - 10)
        
        cv2.imshow("Finger-Card Identification Demo", img)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

    # Cleanup
    cap.release()
    hands.close()
    cv2.destroyAllWindows()
    print("Demo terminated.")

if __name__ == "__main__":
    main()
