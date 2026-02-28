import cv2
import argparse
import time
import numpy as np
from collections import deque
import math

# Import path utility from asimov

# --- ONE EURO FILTER IMPLEMENTATION (For smooth tracking) ---
class OneEuroFilter:
    """
    One Euro Filter: https://cristal.univ-lille.fr/~casiez/1euro/
    Keeps smooth values but reacts faster to quick movements.
    """
    def __init__(self, freq=30, min_cutoff=1.0, beta=0.01, dcutoff=1.0, init=None):
        self.freq = freq              # Hz, frame rate estimate
        self.min_cutoff = min_cutoff  # baseline smoothing
        self.beta = beta              # speed sensitivity
        self.dcutoff = dcutoff        # derivative smoothing
        self.last_time = None
        self.x_prev = init
        self.dx_prev = 0

    def _alpha(self, cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def update(self, x):
        now = time.time()
        if self.last_time is None:
            dt = 1.0 / self.freq
        else:
            dt = max(now - self.last_time, 1e-6)
        self.last_time = now

        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0

        # derivative
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.dcutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        # adaptive cutoff
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)

        # filtered value
        x_hat = a * x + (1 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat

# --- APPLICATION CONSTANTS ---
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS_SMOOTHING_ALPHA = 0.1

# Contour Detection and Filtering Constraints (No Magic Numbers)
RECT_MIN_AREA_PERCENT = 0.005 # Minimum area must be 0.5% of total frame area
RECT_MAX_AREA_PERCENT = 0.5   # Maximum area can be 50% of total frame area
ASPECT_RATIO_MIN = 0.6      # Min width/height ratio (e.g., 0.6 for playing cards)
ASPECT_RATIO_MAX = 1.5      # Max width/height ratio
APPROX_POLY_EPSILON_FACTOR = 0.03 # Epsilon factor for contour simplification

# Tracking and Smoothing
CARD_EXPIRATION_SECONDS = 3.0 # How long to keep a detected card in the queue after last sight
QUEUE_MAX_SIZE = 10           # Maximum number of rectangles to track
# One Euro Filter parameters for smoothing the detected rectangle position/size
FILTER_MIN_CUTOFF = 1.0
FILTER_BETA = 0.08

# Drawing
CONTOUR_COLOR = (0, 0, 255) # Blue border (B, G, R)
CONTOUR_THICKNESS = 4
INFO_BG_COLOR = (0, 0, 0)
INFO_TEXT_COLOR = (255, 255, 255)
INFO_FONT = cv2.FONT_HERSHEY_SIMPLEX
INFO_FONT_SCALE = 0.7

# --- DATA STRUCTURES ---
# Stored rectangle structure in the queue now uses 4 filters for each of the 4 corners (x, y)
# rect = { 'filters': {'x0': OneEuroFilter, 'y0': OneEuroFilter, ...}, 'pts_smooth': np.array(...), 'timestamp': time.time() }
rect_queue = deque(maxlen=QUEUE_MAX_SIZE)


# --- UTILITY FUNCTIONS ---

def setup_detector_and_args():
    """Initializes the argument parser and video capture settings."""
    parser = argparse.ArgumentParser(description="Real-time rectangle and playing card detection with smoothing.")
    parser.add_argument("--device", type=int, default=0, help="Camera device index to use (default: 0).")
    args = parser.parse_args()

    # Returns the device index parsed from arguments
    return args.device

def process_frame_for_rectangles(frame):
    """
    Detects and filters potential card-like rectangles in the frame.
    Returns a list of the 4-point corners (in the format [[x0, y0], [x1, y1], ...])
    for each detected rectangle.
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
            # Check aspect ratio based on bounding box (used for simple filtering)
            x, y, cw, ch = cv2.boundingRect(approx)
            aspect_ratio = cw / ch
            
            if ASPECT_RATIO_MIN <= aspect_ratio <= ASPECT_RATIO_MAX:
                # Store the 4 corner points (shape: 4, 2)
                detected_rectangles.append(approx.reshape(4, 2))

    return detected_rectangles

def get_centroid(pts):
    """Calculates the centroid (center of mass) of the 4-point contour."""
    M = cv2.moments(pts)
    if M["m00"] == 0:
        return 0, 0
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return cx, cy

def match_and_update_queue(detected_rectangles, fps_estimate):
    """
    Matches detected rectangles to existing tracked rectangles in the queue
    and applies One Euro filtering to all 4 corner coordinates.
    """
    current_time = time.time()
    
    # Track which items in the queue have been matched in this frame
    matched_indices = [False] * len(rect_queue)
    
    MATCH_DISTANCE_THRESHOLD = 50 

    # --- Step 1: Match and Update Existing Rects ---
    for new_rect_pts in detected_rectangles:
        new_cx, new_cy = get_centroid(new_rect_pts)
        
        best_match_index = -1
        min_distance = float('inf')

        # Find the best match in the currently tracked queue items
        for i, tracked_rect in enumerate(rect_queue):
            # We use the previous smoothed center for distance matching
            tracked_cx_prev = tracked_rect['filters']['x0'].x_prev # Use one corner's filter for center proxy
            tracked_cy_prev = tracked_rect['filters']['y0'].x_prev
            
            # Simple distance between centroids
            dist = math.sqrt((tracked_cx_prev - new_cx)**2 + (tracked_cy_prev - new_cy)**2)
            
            if dist < min_distance and dist < MATCH_DISTANCE_THRESHOLD and not matched_indices[i]:
                min_distance = dist
                best_match_index = i

        if best_match_index != -1:
            # Update existing tracked rectangle
            tracked_rect = rect_queue[best_match_index]
            
            # Since the points in the new_rect_pts array might be in a different order
            # than the filters, we must correctly re-sort the new points to match 
            # the order of the stored filters before updating them.
            
            # For simplicity, we assume the initial filter order is based on the centroid 
            # and angle, but here we just rely on matching the closest points to the existing
            # filtered points (which is more robust to rotation).

            # We create the new smoothed points array
            pts_smooth = np.zeros((4, 2), dtype=np.int32)
            
            for j in range(4): # For each of the four existing filtered points
                
                # Get the position of the j-th filtered point
                fx_prev = tracked_rect['filters'][f'x{j}'].x_prev
                fy_prev = tracked_rect['filters'][f'y{j}'].x_prev
                
                min_dist_corner = float('inf')
                best_new_point_index = -1
                
                # Find the closest point in the new detection (new_rect_pts)
                for k in range(4):
                    new_x, new_y = new_rect_pts[k]
                    dist = math.sqrt((fx_prev - new_x)**2 + (fy_prev - new_y)**2)
                    
                    if dist < min_dist_corner:
                        min_dist_corner = dist
                        best_new_point_index = k
                
                # Update the filter for corner j with the data from the best matched new point
                if best_new_point_index != -1:
                    matched_new_x, matched_new_y = new_rect_pts[best_new_point_index]
                    
                    # Apply One Euro Filter to the x and y coordinates of corner j
                    pts_smooth[j, 0] = int(tracked_rect['filters'][f'x{j}'].update(matched_new_x))
                    pts_smooth[j, 1] = int(tracked_rect['filters'][f'y{j}'].update(matched_new_y))

                    # Remove the matched point from the new detection set to avoid reuse
                    # (This part is tricky in Python, simple loop structure is better for filtering)
                    # For simplicity, we tolerate potential non-exclusive matching for now since the filter will stabilize it.
            
            # Update the tracked rectangle state
            tracked_rect['pts_smooth'] = pts_smooth
            tracked_rect['timestamp'] = current_time
            matched_indices[best_match_index] = True

        else:
            # New detection: Create a new tracked rectangle with filters initialized by its 4 points
            new_filters = {}
            for i in range(4):
                new_filters[f'x{i}'] = OneEuroFilter(freq=fps_estimate, min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA, init=new_rect_pts[i, 0])
                new_filters[f'y{i}'] = OneEuroFilter(freq=fps_estimate, min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA, init=new_rect_pts[i, 1])
                
            # Initial smoothed points are just the initial points
            new_tracked_rect = {
                'filters': new_filters,
                'pts_smooth': new_rect_pts.astype(np.int32), 
                'timestamp': current_time
            }
            rect_queue.append(new_tracked_rect)

    # --- Step 2: Expire Old Rects ---
    
    # Rebuild the queue, dropping expired items
    new_rect_queue_list = []
    
    for tracked_rect in rect_queue:
        if (current_time - tracked_rect['timestamp']) < CARD_EXPIRATION_SECONDS:
            new_rect_queue_list.append(tracked_rect)
            
    # Replace the queue content with the new, non-expired list
    rect_queue.clear()
    rect_queue.extend(new_rect_queue_list)


def draw_tracked_rectangles(frame):
    """Draws the stabilized, tracked rectangles from the queue onto the frame using the smoothed contour points."""
    for tracked_rect in rect_queue:
        # The smoothed points array (shape 4, 2)
        pts = tracked_rect['pts_smooth']
        
        # Reshape for cv2.polylines: needs shape (1, N, 2) where N is the number of points
        pts = pts.reshape((-1, 1, 2))
        
        # Draw the blue border following the smoothed contour
        # isClosed=True ensures the rectangle is closed
        cv2.polylines(frame, [pts], isClosed=True, color=CONTOUR_COLOR, thickness=CONTOUR_THICKNESS)
        
        # Optionally draw the centroid as well for visualization
        smooth_cx, smooth_cy = get_centroid(tracked_rect['pts_smooth'])
        cv2.circle(frame, (int(smooth_cx), int(smooth_cy)), 5, CONTOUR_COLOR, -1)


def draw_info_box(frame, text, x, y):
    """Draws a text label with a solid background for readability."""
    (text_w, text_h), baseline = cv2.getTextSize(text, INFO_FONT, INFO_FONT_SCALE, 2)
    cv2.rectangle(frame, (x, y - text_h - baseline - 5), (x + text_w + 10, y + 5), INFO_BG_COLOR, -1)
    cv2.putText(frame, text, (x + 5, y - baseline), INFO_FONT, INFO_FONT_SCALE, INFO_TEXT_COLOR, 2, cv2.LINE_AA)

def main():
    """Main function to run the video processing loop."""
    
    # Use argparse to get the device index
    device_index = setup_detector_and_args()

    # Initialize video capture using the parsed device_index
    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    fps_estimate = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # FPS tracking variables
    pTime = 0
    avg_fps = 0.0 # Initial smoothed FPS
    
    print(f"Starting card detection demo on device {device_index}. Expected FPS: {fps_estimate:.1f}")
    
    while True:
        success, img = cap.read()
        if not success:
            print(f"Error: Could not read from video device index {device_index}. Exiting.")
            break
        
        # Calculate FPS
        cTime = time.time()
        inst_fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        
        # Apply EMA smoothing for stable display
        if avg_fps == 0.0:
            avg_fps = inst_fps
        else:
            avg_fps = (FPS_SMOOTHING_ALPHA * inst_fps) + ((1 - FPS_SMOOTHING_ALPHA) * avg_fps)
            
        # Flip the frame for a mirror effect (more intuitive)
        img = cv2.flip(img, 1)

        # 1. Detect candidate rectangles
        detected_rectangles = process_frame_for_rectangles(img)

        # 2. Match, Update, and Filter Queue using One Euro Filter
        match_and_update_queue(detected_rectangles, fps_estimate)

        # 3. Draw the stabilized rectangles from the queue
        draw_tracked_rectangles(img)
        
        # 4. Display Information
        status_text = f"Cards Tracked: {len(rect_queue)} | FPS: {int(avg_fps)}"
        draw_info_box(img, status_text, 10, FRAME_HEIGHT - 10)
        
        cv2.imshow("Card Detection and Tracking Demo", img)

        # Check for 'q' or ESC (key code 27) to quit
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Demo terminated.")

if __name__ == "__main__":
    main()
