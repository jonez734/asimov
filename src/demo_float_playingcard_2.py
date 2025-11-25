import cv2
import argparse
import time
import random
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from asimov.util import safe_path

# --- CONSTANTS ---
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
GLITCH_MAX_DURATION = 0.05  # Max duration in seconds the glitch state is active
GLITCH_INTERVAL_MIN = 3.0   # Minimum time (seconds) between glitch events
GLITCH_INTERVAL_MAX = 7.0   # Maximum time (seconds) between glitch events
PALM_SCALE_FACTOR = 1.5     # Factor to size the card relative to the palm bounding box width
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_COLOR = (255, 255, 255)
TEXT_BG_COLOR = (0, 0, 0)

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

def apply_glitch_effect(image):
    """Applies a brief, noticeable visual distortion (glitch) to the image."""
    h, w, _ = image.shape
    glitched_img = image.copy()

    # 1. Random horizontal shift (flickering)
    shift_amount = random.randint(-10, 10)
    if shift_amount > 0:
        glitched_img[:, shift_amount:] = image[:, :-shift_amount]
        glitched_img[:, :shift_amount] = 0 # Black fill
    elif shift_amount < 0:
        shift_amount = abs(shift_amount)
        glitched_img[:, :-shift_amount] = image[:, shift_amount:]
        glitched_img[:, -shift_amount:] = 0 # Black fill

    # 2. Color channel separation (randomly shift G or B channel)
    b, g, r, a = cv2.split(glitched_img)
    if random.choice([True, False]):
        g = np.roll(g, random.randint(-5, 5), axis=1)
    else:
        b = np.roll(b, random.randint(-5, 5), axis=0)

    # 3. Random noise/scan lines (apply to a small region)
    y_start = random.randint(0, h // 2)
    y_end = random.randint(h // 2, h)
    glitched_img[y_start:y_end, :, :3] = cv2.addWeighted(glitched_img[y_start:y_end, :, :3], 0.7, np.random.randint(0, 255, (y_end - y_start, w, 3), dtype=np.uint8), 0.3, 0)

    glitched_img = cv2.merge([b, g, r, a])
    return glitched_img

def overlay_image_on_frame(frame, card_img, bbox):
    """
    Resizes the card image based on the hand bounding box and overlays it onto the frame.
    bbox is [x, y, w, h] of the hand.
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
    alpha_channel = card_to_overlay[:, :, 3] / 255.0
    color_channels = card_to_overlay[:, :, :3]

    # Extract the ROI from the frame
    roi = frame[y1_final:y2_final, x1_final:x2_final]

    # Blend the images
    for c in range(0, 3):
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
    
    # Setup initial components, now receiving the device_index
    card_path, device_index, detector = setup_detector_and_args()

    card_path = safe_path(card_path)
    
    original_card_img = load_card_image(card_path)

    # Initialize video capture using the parsed device index
    cap = cv2.VideoCapture(device_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    # Glitch state variables
    last_glitch_time = time.time()
    next_glitch_interval = random.uniform(GLITCH_INTERVAL_MIN, GLITCH_INTERVAL_MAX)
    is_glitching = False
    glitch_start_time = 0

    while True:
        success, img = cap.read()
        if not success:
            print(f"Error: Could not read from video device index {device_index}. Exiting.")
            break

        # Flip the frame for a mirror effect (more intuitive)
        img = cv2.flip(img, 1)

        # 1. Hand Detection
        # Finds hands and draws landmarks/bounding box by default
        hands, img = detector.findHands(img, draw=True)

        info_text = "Status: Card hidden (Close hand or no hand detected)"
        current_card_img = original_card_img.copy()

        if hands:
            # We focus on the first detected hand
            hand = hands[0]
            bbox = hand["bbox"]  # [x, y, w, h] of the hand bounding box
            
            # 2. Check Finger State
            # list of 5 (1=up, 0=down): [thumb, index, middle, ring, pinky]
            finger_list = detector.fingersUp(hand) 
            
            # Check if all 5 fingers are up (open palm)
            if all(finger_list):
                info_text = "Status: Card floating (Open Palm Detected)"

                # 3. Glitch Logic
                current_time = time.time()
                
                # Check if it's time to start a new glitch
                if not is_glitching and (current_time - last_glitch_time) > next_glitch_interval:
                    is_glitching = True
                    glitch_start_time = current_time
                    # Pre-calculate next interval immediately after triggering
                    last_glitch_time = current_time
                    next_glitch_interval = random.uniform(GLITCH_INTERVAL_MIN, GLITCH_INTERVAL_MAX)
                    
                # Check if the current glitch should end
                if is_glitching and (current_time - glitch_start_time) > GLITCH_MAX_DURATION:
                    is_glitching = False

                # Apply glitch effect if state is active
                if is_glitching:
                    current_card_img = apply_glitch_effect(current_card_img)
                    info_text += " - GLITCH ACTIVE!"
                
                # 4. Overlay the card
                img = overlay_image_on_frame(img, current_card_img, bbox)

            else:
                info_text = f"Status: Fingers up: {sum(finger_list)}/5 (Close palm)"

        # 5. Display Information and Frame
        draw_info_box(img, info_text, 10, FRAME_HEIGHT - 10)
        
        cv2.imshow("Demo Float Playing Card", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Demo terminated.")

if __name__ == "__main__":
    main()
