import cv2
import argparse
import time
import numpy as np
from cvzone.HandTrackingModule import HandDetector
# Removed cvzone.Utils.fps import to use manual time.time() calculation.

# Import the external glitch module and path utility from asimov
from asimov import glitch
from asimov.util import safe_path

# --- APPLICATION CONSTANTS ---
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
PALM_SCALE_FACTOR = 1.5     # Factor to size the card relative to the palm bounding box width
DEFAULT_OPACITY = 0.8       # Default card transparency (0.0=invisible, 1.0=opaque)
GLITCH_OPACITY = 0.5        # Opacity while any glitch is active
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_COLOR = (255, 255, 255)
TEXT_BG_COLOR = (0, 0, 0)

# NOTE: Removed local _frame_history deque and glitch function definitions.
# All glitch effect logic and state (like frame history for 'ghost') is now
# assumed to be handled within the imported 'glitch' module.

# --- UTILITY FUNCTIONS ---

def setup_detector_and_args():
    """Initializes the argument parser, retrieves card path and device index, and sets up the HandDetector."""
    parser = argparse.ArgumentParser(description="Float a playing card graphic over an open palm.")
    parser.add_argument("--card", type=str, required=True, help="Path to the PNG playing card image.")
    parser.add_argument("--device", type=int, default=0, help="Camera device index to use (default: 0).")
    args = parser.parse_args()

    # Initialize Hand Detector (0.8 minimum detection confidence)
    detector = HandDetector(detectionCon=0.7, maxHands=1)

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

    # --- GLITCH FRAMEWORK INITIALIZATION (Using external module) ---
    
    # Set the max number of concurrent glitches
    glitch.set_max_concurrent(2)
    
    # Register the required glitch types by passing only the base name.
    glitch.register("scanlines")
    glitch.register("vhs_warp", intensity=7, frequency=3.0, speed=1.5)
    glitch.register("ghost", alpha=0.3, shift=8)

    # Initialize video capture using the parsed device index
    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    # State variable for dynamic opacity
    current_opacity = DEFAULT_OPACITY
    
    # FPS tracking variables
    pTime = 0

    while True:
        success, img = cap.read()
        if not success:
            print(f"Error: Could not read from video device index {device_index}. Exiting.")
            break
        
        # Calculate FPS manually using time.time()
        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        fps_text = f"FPS: {int(fps)}"

        # Flip the frame for a mirror effect (more intuitive)
        img = cv2.flip(img, 1)

        # 1. Hand Detection
        hands, img = detector.findHands(img, draw=True, flipType=False)

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
                
                # 3. Glitch Logic: Check timing and update active states using the imported scheduler
                glitch.scheduler()
                
                # 4. Dynamic Opacity and Glitch Application
                if glitch.is_any_glitch_running():
                    # Apply all active glitches using the external framework (glitch.apply())
                    current_card_img = glitch.apply(current_card_img)
                    current_opacity = GLITCH_OPACITY # Set lower opacity during glitch
                    
                    # Create status text listing active glitches
                    info_text = f"Status: Card floating ({current_opacity * 100:.0f}%) - GLITCH ACTIVE"
                else:
                    current_opacity = DEFAULT_OPACITY # Revert to default opacity
                    info_text = f"Status: Card floating ({current_opacity * 100:.0f}%)"
                
                # 5. Overlay the card
                img = overlay_image_on_frame(img, current_card_img, bbox, current_opacity)

            else:
                # Hand detected but not open palm
                info_text = f"Status: Fingers up: {sum(finger_list)}/5 (Close palm)"

        # 6. Display Information and Frame
        # Combine status text and FPS text
        full_status_text = f"{info_text} | {fps_text}"
        draw_info_box(img, full_status_text, 10, FRAME_HEIGHT - 10)
        
        cv2.imshow("Demo Float Playing Card", img)

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
