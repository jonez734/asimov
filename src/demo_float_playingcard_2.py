import cv2
import argparse
import time
import random
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from dataclasses import dataclass, field
from typing import Optional, Callable
from collections import deque

# User specified import for path handling (requires 'asimov' package to be installed)
from asimov.util import safe_path

# --- CORE GLITCH FRAMEWORK CONSTANTS (from glitch.py) ---
MIN_DURATION = 0.3          # Minimum duration a glitch effect runs (seconds)
MAX_DURATION = 1.2          # Maximum duration a glitch effect runs (seconds)
MIN_INTERVAL = 3.0          # Minimum time between glitch starts (seconds)
MAX_INTERVAL = 7.0          # Maximum time between glitch starts (seconds)

# --- APPLICATION CONSTANTS ---
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
PALM_SCALE_FACTOR = 1.5     # Factor to size the card relative to the palm bounding box width
DEFAULT_OPACITY = 0.8       # Default card transparency (0.0=invisible, 1.0=opaque)
GLITCH_OPACITY = 0.5        # Opacity while any glitch is active
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_COLOR = (255, 255, 255)
TEXT_BG_COLOR = (0, 0, 0)

# --- GLITCH STATE MANAGEMENT (Based on glitch.py) ---

@dataclass
class Glitch:
    """Dataclass to hold the state of a single glitch effect."""
    name: str
    func: Callable
    running: bool = False
    active_start: Optional[float] = 0.0
    duration: Optional[float] = 0.0
    last_trigger: float = 0.0
    trigger_interval: float = 0.0
    kwargs: dict = field(default_factory=dict)

# Global state dictionaries
_glitches: dict[str, Glitch] = {}
_frame_history = deque(maxlen=5) # History for ghost/datamosh effects

def register_glitch(name: str, func: Callable, **kwargs):
    """Register a new glitch effect with its function and initial settings."""
    g = Glitch(name=name, func=func, kwargs=kwargs)
    g.last_trigger = time.time()
    g.trigger_interval = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
    _glitches[name] = g

def start_glitch(name: str, duration: float):
    """Mark a registered glitch as running for a specific duration."""
    g = _glitches.get(name)
    if g:
        g.running = True
        g.active_start = time.time()
        g.duration = duration

def is_any_glitch_running():
    """Returns True if at least one registered glitch is currently active."""
    return any(g.running for g in _glitches.values())

def manage_glitch_scheduler():
    """Checks timing and starts/stops glitches based on defined intervals/durations."""
    now = time.time()
    
    for name, glitch in list(_glitches.items()):
        
        # 1. Stop glitches that have run their course
        if glitch.running and now - glitch.active_start >= glitch.duration:
            glitch.running = False
            glitch.last_trigger = now  # Mark when it finished
            # Clear history for effects like 'ghost' when they stop
            if name == 'ghost':
                 _frame_history.clear() 

        # 2. Maybe trigger new glitches
        elif not glitch.running:
            if now - glitch.last_trigger >= glitch.trigger_interval:
                # Start new random duration
                duration = random.uniform(MIN_DURATION, MAX_DURATION)
                start_glitch(name, duration)
                # Update next trigger interval now
                glitch.trigger_interval = random.uniform(MIN_INTERVAL, MAX_INTERVAL)

# --- GLITCH EFFECT FUNCTIONS (Based on glitch.py) ---

def glitch_scanlines(frame, t=None, **kwargs):
    """Overlays simple static scanlines (darkens every other row)."""
    output = frame.copy()
    # Simple static scanlines for short effect (darkens half the pixels)
    output[::2, :, :] = (output[::2, :, :] * 0.5).astype(np.uint8)
    return output

def glitch_vhs_warp(frame, t=None, intensity=5, frequency=2.0, speed=1.0, **kwargs):
    """Simulate VHS horizontal warping using a sine wave function."""
    h, w, c = frame.shape
    # Create an empty output image with the same dimensions
    output = np.zeros_like(frame)
    
    # Create vertical coordinate grid
    y = np.arange(h)
    
    # Compute horizontal offsets using a sinusoidal function of y (vertical position) and t (time)
    offsets = (intensity * np.sin(2 * np.pi * frequency * (y / h) + speed * t)).astype(np.int32)
    
    for row in range(h):
        shift = offsets[row]
        if shift > 0:
            # Shift right (pulling data from the left)
            output[row, shift:] = frame[row, :-shift]
        elif shift < 0:
            # Shift left (pulling data from the right)
            output[row, :shift] = frame[row, -shift:]
        else:
            output[row] = frame[row]

    return output

def glitch_ghost(frame, alpha: float = 0.4, shift: int = 5, **kwargs):
    """Ghosting effect: overlays a faded, shifted older frame."""
    global _frame_history
    h, w = frame.shape[:2]
    
    # Add current frame to history
    _frame_history.append(frame.copy())
    
    if len(_frame_history) < 2:
        return frame
    
    # Use the oldest frame (index 0) as the ghost
    ghost_frame = _frame_history[0]

    # Shift ghost frame horizontally (like a CRT lag)
    M = np.float32([[1, 0, shift], [0, 1, 0]])
    shifted = cv2.warpAffine(ghost_frame, M, (w, h))

    # Blend ghost with current frame (current frame is 1.0 weight, ghost is alpha weight)
    return cv2.addWeighted(frame, 1.0, shifted, alpha, 0)

def apply_glitches_to_image(image):
    """Iterates through all running glitches and applies them sequentially to the image."""
    now = time.time()
    current_image = image.copy()
    
    for glitch in _glitches.values():
        if glitch.running:
            elapsed = now - glitch.active_start
            # Pass the current image through the glitch function
            current_image = glitch.func(current_image, t=elapsed, **glitch.kwargs)
    
    return current_image

# --- UTILITY FUNCTIONS ---

def setup_detector_and_args():
    """Initializes the argument parser, retrieves card path and device index, and sets up the HandDetector."""
    parser = argparse.ArgumentParser(description="Float a playing card graphic over an open palm.")
    parser.add_argument("--card", type=str, required=True, help="Path to the PNG playing card image.")
    # Added new argument for camera device selection
    parser.add_argument("--device", type=int, default=0, help="Camera device index to use (default: 0).")
    args = parser.parse_args()

    # Initialize Hand Detector (0.8 minimum detection confidence)
    detector = HandDetector(detectionCon=0.8, maxHands=1)

    # Return card path, device index, and detector
    return args.card, args.device, detector

def load_card_image(card_path):
    """Loads the PNG card image with an alpha channel."""
    try:
        # Run the card_path through the safety function
        card_path = safe_path(card_path)

        card_img = cv2.imread(card_path, cv2.IMREAD_UNCHANGED)
        if card_img is None:
            raise FileNotFoundError(f"Image not found at path: {card_path}")
        if card_img.shape[2] != 4:
            print("Warning: Card image does not have 4 channels (alpha). Adding dummy alpha channel.")
            b, g, r = cv2.split(card_img)
            alpha = np.ones(b.shape, dtype=b.dtype) * 255
            card_img = cv2.merge([b, g, r, alpha])

        return card_img
    except Exception as e:
        print(f"Error loading card image: {e}")
        exit()

def overlay_image_on_frame(frame, card_img, bbox, card_opacity):
    """
    Resizes the card image based on the hand bounding box and overlays it onto the frame.
    Applies card_opacity to the image's alpha channel for dynamic transparency.
    """
    # 1. Determine size and position
    hand_w = bbox[2]
    target_w = int(hand_w * PALM_SCALE_FACTOR)
    
    # Calculate target height while maintaining aspect ratio
    original_h, original_w, _ = card_img.shape
    target_h = int((target_w / original_w) * original_h)

    if target_w < 10 or target_h < 10:
        return frame # Safety check for extremely small hands

    # 2. Resize card
    resized_card = cv2.resize(card_img, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # 3. Calculate anchor point (center of the hand bounding box, slightly elevated)
    center_x = bbox[0] + hand_w // 2
    center_y = bbox[1] + bbox[3] // 4 # Anchor higher up, near the palm center

    # 4. Calculate top-left corner for overlay
    x1 = int(center_x - target_w // 2)
    y1 = int(center_y - target_h // 2)
    x2 = x1 + target_w
    y2 = y1 + target_h

    # 5. Clamp coordinates to frame boundaries
    h_frame, w_frame, _ = frame.shape
    
    x1_final = max(0, x1)
    y1_final = max(0, y1)
    x2_final = min(w_frame, x2)
    y2_final = min(h_frame, y2)

    # Calculate crop based on clamped boundaries
    card_crop_x1 = x1_final - x1
    card_crop_y1 = y1_final - y1
    card_crop_x2 = target_w - (x2 - x2_final)
    card_crop_y2 = target_h - (y2 - y2_final)

    # 6. Overlay the image using the alpha channel
    card_to_overlay = resized_card[card_crop_y1:card_crop_y2, card_crop_x1:card_crop_x2]

    # Get alpha channel and the color BGR channels
    # Apply the user-defined card_opacity to the image's existing alpha channel
    alpha_channel = (card_to_overlay[:, :, 3] / 255.0) * card_opacity 
    color_channels = card_to_overlay[:, :, :3]

    # Extract the ROI from the frame
    roi = frame[y1_final:y2_final, x1_final:x2_final]

    # Blend the images
    for c in range(0, 3):
        # Weighted sum: (Background * (1 - Alpha)) + (Foreground * Alpha)
        roi[:, :, c] = (roi[:, :, c] * (1 - alpha_channel)) + (color_channels[:, :, c] * alpha_channel)

    frame[y1_final:y2_final, x1_final:x2_final] = roi
    
    return frame

def draw_info_box(frame, text, x, y):
    """Draws a text label with a solid background for readability."""
    (text_w, text_h), baseline = cv2.getTextSize(text, FONT, 0.7, 2)
    cv2.rectangle(frame, (x, y - text_h - baseline - 5), (x + text_w + 10, y + 5), TEXT_BG_COLOR, -1)
    cv2.putText(frame, text, (x + 5, y - baseline), FONT, 0.7, TEXT_COLOR, 2, cv2.LINE_AA)

def main():
    """Main function to run the video processing loop."""
    
    # Setup initial components
    card_path, device_index, detector = setup_detector_and_args()
    original_card_img = load_card_image(card_path)

    # --- GLITCH INITIALIZATION ---
    # Register the required glitch types
    register_glitch("scanlines", glitch_scanlines)
    register_glitch("vhs_warp", glitch_vhs_warp, intensity=7, frequency=3.0, speed=1.5)
    register_glitch("ghost", glitch_ghost, alpha=0.3, shift=8)

    # Initialize video capture using the parsed device index
    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    # State variable for dynamic opacity
    current_opacity = DEFAULT_OPACITY

    while True:
        success, img = cap.read()
        if not success:
            print(f"Error: Could not read from video device index {device_index}. Exiting.")
            break

        # Flip the frame for a mirror effect (more intuitive)
        img = cv2.flip(img, 1)

        # 1. Hand Detection
        hands, img = detector.findHands(img, draw=True)

        info_text = "Status: Card hidden (Close hand or no hand detected)"
        current_card_img = original_card_img.copy()

        if hands:
            # We focus on the first detected hand
            hand = hands[0]
            bbox = hand["bbox"]  # [x, y, w, h] of the hand bounding box
            
            # 2. Check Finger State: list of 5 (1=up, 0=down)
            finger_list = detector.fingersUp(hand) 
            
            # Check if all 5 fingers are up (open palm)
            if all(finger_list):
                
                # 3. Glitch Logic: Check timing and update active states
                manage_glitch_scheduler()
                
                # 4. Dynamic Opacity and Glitch Application
                if is_any_glitch_running():
                    current_card_img = apply_glitches_to_image(current_card_img)
                    current_opacity = GLITCH_OPACITY # Set lower opacity during glitch
                    
                    # Create status text listing active glitches
                    active_names = ", ".join([g.name for g in _glitches.values() if g.running])
                    info_text = f"Status: Card floating ({current_opacity * 100:.0f}%) - GLITCH ACTIVE: {active_names}"
                else:
                    current_opacity = DEFAULT_OPACITY # Revert to default opacity
                    info_text = f"Status: Card floating ({current_opacity * 100:.0f}%)"
                
                # 5. Overlay the card
                img = overlay_image_on_frame(img, current_card_img, bbox, current_opacity)

            else:
                # Hand detected but not open palm
                info_text = f"Status: Fingers up: {sum(finger_list)}/5 (Close palm)"

        # 6. Display Information and Frame
        draw_info_box(img, info_text, 10, FRAME_HEIGHT - 10)
        
        cv2.imshow("Demo Float Playing Card", img)

        ch = cv2.waitKey(1) & 0xFF 
        if ch == ord('q') or ch == 27:
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Demo terminated.")

if __name__ == "__main__":
    main()
