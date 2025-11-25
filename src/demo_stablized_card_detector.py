import cv2
import argparse
import time
import numpy as np
from collections import deque
import math

# Import path utility from asimov
from asimov.util import safe_path

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
CONTOUR_COLOR = (255, 128, 0) # Orange/Blue color for border
CONTOUR_THICKNESS = 4
INFO_BG_COLOR = (0, 0, 0)
INFO_TEXT_COLOR = (255, 255, 255)
INFO_FONT = cv2.FONT_HERSHEY_SIMPLEX
INFO_FONT_SCALE = 0.7

# --- DATA STRUCTURES ---
# Stored rectangle structure in the queue
# rect = { 'pts': np.array([[x1, y1], [x2, y2], [x3, y3], [x4, y4]]), 'timestamp': time.time(), 'filter_x': OneEuroFilter, ... }
rect_queue = deque(maxlen=QUEUE_MAX_SIZE)


# --- UTILITY FUNCTIONS ---

def setup_detector_and_args():
    """Initializes the argument parser and video capture settings."""
    parser = argparse.ArgumentParser(description="Real-time rectangle and playing card detection with smoothing.")
    parser.add_argument("--device", type=int, default=0, help="Camera device index to use (default: 0).")
    args = parser.parse_args()

    return args.device

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
    # RETR_EXTERNAL retrieves only the outer extreme contours
    # CHAIN_APPROX_SIMPLE compresses horizontal, vertical, and diagonal segments
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
        # We look for a shape with 4 vertices
        if len(approx) == 4:
            # Get bounding box of the 4-vertex shape
            x, y, cw, ch = cv2.boundingRect(approx)
            
            # Aspect Ratio Check
            aspect_ratio = cw / ch
            if ASPECT_RATIO_MIN <= aspect_ratio <= ASPECT_RATIO_MAX:
                # The contour is a strong candidate for a rectangle (card)
                # We save the actual 4 corner points for drawing/smoothing
                detected_rectangles.append(approx.reshape(-1, 2))

    return detected_rectangles

def match_and_update_queue(detected_rectangles, fps_estimate):
    """
    Matches detected rectangles to existing tracked rectangles in the queue
    and applies One Euro filtering for stabilization.
    """
    current_time = time.time()
    unmatched_queue_indices = list(range(len(rect_queue)))
    
    # Use a high threshold for distance matching (e.g., 50 pixels)
    MATCH_DISTANCE_THRESHOLD = 50 

    # --- Step 1: Match and Update Existing Rects ---
    for new_rect_pts in detected_rectangles:
        # Calculate the center of the new detection
        M = cv2.moments(new_rect_pts)
        if M["m00"] == 0: continue
        new_cx = M["m10"] / M["m00"]
        new_cy = M["m01"] / M["m00"]
        
        best_match_index = -1
        min_distance = float('inf')

        for i in unmatched_queue_indices:
            tracked_rect = rect_queue[i]
            # Compare center points of the tracked and new rectangle
            dist = math.sqrt((tracked_rect['cx'].x_prev - new_cx)**2 + (tracked_rect['cy'].x_prev - new_cy)**2)
            
            if dist < min_distance and dist < MATCH_DISTANCE_THRESHOLD:
                min_distance = dist
                best_match_index = i

        if best_match_index != -1:
            # Update existing tracked rectangle
            tracked_rect = rect_queue[best_match_index]

            # Apply One Euro Filter to position and size/angle
            tracked_rect['cx'].update(new_cx)
            tracked_rect['cy'].update(new_cy)
            tracked_rect['timestamp'] = current_time
            
            # Mark as matched
            unmatched_queue_indices.remove(best_match_index)
        else:
            # New detection: Create a new tracked rectangle with filters
            new_tracked_rect = {
                'cx': OneEuroFilter(freq=fps_estimate, min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA, init=new_cx),
                'cy': OneEuroFilter(freq=fps_estimate, min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA, init=new_cy),
                # Storing the latest 4-points (for drawing reference)
                'pts': new_rect_pts, 
                'timestamp': current_time
            }
            rect_queue.append(new_tracked_rect)

    # --- Step 2: Expire Old and Unmatched Rects ---
    # Convert unmatched indices to actual indices in the queue (since the list changes)
    
    # The simplest way to handle expiration without complex index tracking is to rebuild the queue
    # in a new list, dropping expired items, and then replacing the queue content.
    new_rect_queue_list = []
    
    for tracked_rect in rect_queue:
        # If it was matched in this frame, its timestamp is current_time.
        # If it wasn't matched, its timestamp is older.
        if (current_time - tracked_rect['timestamp']) < CARD_EXPIRATION_SECONDS:
            new_rect_queue_list.append(tracked_rect)
            
    # Replace the queue content with the new, non-expired list
    rect_queue.clear()
    rect_queue.extend(new_rect_queue_list)


def draw_tracked_rectangles(frame):
    """Draws the stabilized, tracked rectangles from the queue onto the frame."""
    for tracked_rect in rect_queue:
        # Get the smoothed center position
        smooth_cx = int(tracked_rect['cx'].x_prev)
        smooth_cy = int(tracked_rect['cy'].x_prev)
        
        # NOTE: Since we are not smoothing size/angle yet, we use a simple bounding box
        # from the latest 'pts' detection for drawing size approximation.
        # For a truly smooth effect, we would need to filter all 4 corners or w/h/angle.
        
        # Calculate bounding box from the last detected points
        x, y, w, h = cv2.boundingRect(tracked_rect['pts'])
        
        # Create a basic rectangular contour centered on the smoothed position
        # This gives a "floating" effect, where the position is smooth but the size/shape might flicker slightly
        half_w, half_h = w // 2, h // 2
        
        # Calculate top-left and bottom-right corners based on smoothed center
        pt1 = (smooth_cx - half_w, smooth_cy - half_h)
        pt2 = (smooth_cx + half_w, smooth_cy + half_h)
        
        # Draw the smoothed rectangle border
        cv2.rectangle(frame, pt1, pt2, CONTOUR_COLOR, CONTOUR_THICKNESS)
        
        # Draw center point for visualization
        cv2.circle(frame, (smooth_cx, smooth_cy), 5, CONTOUR_COLOR, -1)


def draw_info_box(frame, text, x, y):
    """Draws a text label with a solid background for readability."""
    (text_w, text_h), baseline = cv2.getTextSize(text, INFO_FONT, INFO_FONT_SCALE, 2)
    cv2.rectangle(frame, (x, y - text_h - baseline - 5), (x + text_w + 10, y + 5), INFO_BG_COLOR, -1)
    cv2.putText(frame, text, (x + 5, y - baseline), INFO_FONT, INFO_FONT_SCALE, INFO_TEXT_COLOR, 2, cv2.LINE_AA)


def main():
    """Main function to run the video processing loop."""
    
    device_index = setup_detector_and_args()

    # Initialize video capture
    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    fps_estimate = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # FPS tracking variables
    pTime = 0
    avg_fps = 0.0 # Initial smoothed FPS
    
    print(f"Starting card detection demo. Expected FPS: {fps_estimate:.1f}")
    
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
