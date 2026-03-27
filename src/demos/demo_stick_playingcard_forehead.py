import cv2
import argparse
import time
import numpy as np

# NOTE: Switched from HandDetector to FaceMeshDetector to find the forehead
from cvzone.FaceMeshModule import FaceMeshDetector

# Import the external glitch module and path utility from asimov
from asimov import glitch
from asimov.util import safe_path

# --- APPLICATION CONSTANTS ---
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
# Factor now sizes the card relative to the face width (0.5 means half the face width)
FOREHEAD_SCALE_FACTOR = 0.5
DEFAULT_OPACITY = 0.8  # Default card transparency (0.0=invisible, 1.0=opaque)
GLITCH_OPACITY = 0.5  # Opacity while any glitch is active
FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_COLOR = (255, 255, 255)
TEXT_BG_COLOR = (0, 0, 0)

# FPS Smoothing and Font Scaling Configuration
SMOOTHING_ALPHA = (
    0.1  # Alpha for EMA smoothing on FPS (closer to 1 = less smoothing, more flicker)
)
COORDINATE_SMOOTHING_ALPHA = (
    0.3  # Alpha for EMA smoothing on coordinates (lower = more smoothing, more lag)
)
BASE_FONT_SCALE = 0.7  # Reference font scale for 720p height
BASE_HEIGHT_REF = 720  # Reference height for proportional scaling

# --- UTILITY FUNCTIONS ---


def setup_detector_and_args():
    """Initializes the argument parser, retrieves card path and device index, and sets up the FaceMeshDetector."""
    parser = argparse.ArgumentParser(
        description="Stick a playing card graphic to the center of the user's forehead."
    )
    parser.add_argument(
        "--card", type=str, required=True, help="Path to the PNG playing card image."
    )
    parser.add_argument(
        "--device", type=int, default=0, help="Camera device index to use (default: 0)."
    )
    args = parser.parse_args()

    # Initialize Face Mesh Detector (maxFaces=1 to focus on a single user)
    detector = FaceMeshDetector(maxFaces=1)

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
            print(
                "Warning: Card image does not have 4 channels (alpha). Adding dummy alpha channel."
            )
            b, g, r = cv2.split(card_img)
            alpha = np.ones(b.shape, dtype=b.dtype) * 255
            card_img = cv2.merge([b, g, r, alpha])

        return card_img
    except Exception as e:
        print(f"Error loading card image: {e}")
        exit()


def overlay_card_on_forehead(
    frame, card_img, forehead_center, face_width, card_opacity
):
    """
    Sizes the card relative to the detected face width and overlays it onto the frame,
    centered on the forehead landmark.
    """
    # 1. Determine size
    # Target width is based on a factor of the face width
    target_w = int(face_width * FOREHEAD_SCALE_FACTOR)

    # Calculate target height while maintaining aspect ratio
    original_h, original_w, _ = card_img.shape
    target_h = int((target_w / original_w) * original_h)

    if target_w < 10 or target_h < 10:
        return frame  # Safety check for extremely small faces

    # 2. Resize card
    resized_card = cv2.resize(
        card_img, (target_w, target_h), interpolation=cv2.INTER_AREA
    )

    # 3. Calculate top-left corner for overlay, centered on the forehead_center
    x_center, y_center = forehead_center
    x1 = int(x_center - target_w // 2)
    y1 = int(y_center - target_h // 2)
    x2 = x1 + target_w
    y2 = y1 + target_h

    # 4. Clamp coordinates to frame boundaries
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

    # 5. Overlay the image using the alpha channel
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
        roi[:, :, c] = (roi[:, :, c] * (1 - alpha_channel)) + (
            color_channels[:, :, c] * alpha_channel
        )

    frame[y1_final:y2_final, x1_final:x2_final] = roi

    return frame


def draw_info_box(frame, text, x, y):
    """Draws a text label with a solid background for readability, scaling font size based on frame height."""
    h_frame = frame.shape[0]

    # Calculate font scale proportionally to BASE_HEIGHT_REF (720p)
    font_scale = BASE_FONT_SCALE * (h_frame / BASE_HEIGHT_REF)
    # Scale thickness as well, ensuring it's at least 1
    thickness = max(1, int(2 * (h_frame / BASE_HEIGHT_REF)))

    (text_w, text_h), baseline = cv2.getTextSize(text, FONT, font_scale, thickness)
    cv2.rectangle(
        frame,
        (x, y - text_h - baseline - 5),
        (x + text_w + 10, y + 5),
        TEXT_BG_COLOR,
        -1,
    )
    cv2.putText(
        frame,
        text,
        (x + 5, y - baseline),
        FONT,
        font_scale,
        TEXT_COLOR,
        thickness,
        cv2.LINE_AA,
    )


def main():
    """Main function to run the video processing loop."""

    # Setup initial components
    card_path, device_index, detector = setup_detector_and_args()
    original_card_img = load_card_image(card_path)

    # --- GLITCH FRAMEWORK INITIALIZATION (Using external module) ---
    glitch.set_max_concurrent(2)
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
    avg_fps = 0.0  # Initial smoothed FPS

    # --- COORDINATE SMOOTHING STATE ---
    # Initialize smoothed coordinates to None (or 0)
    _smooth_forehead_x = 0
    _smooth_forehead_y = 0
    # ----------------------------------

    while True:
        success, img = cap.read()
        if not success:
            print(
                f"Error: Could not read from video device index {device_index}. Exiting."
            )
            break

        # Calculate FPS manually
        cTime = time.time()
        inst_fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime

        # Apply EMA smoothing for stable display
        if avg_fps == 0.0:
            avg_fps = inst_fps
        else:
            avg_fps = (SMOOTHING_ALPHA * inst_fps) + ((1 - SMOOTHING_ALPHA) * avg_fps)

        fps_text = f"FPS: {int(avg_fps)}"

        # Flip the frame for a mirror effect (more intuitive)
        img = cv2.flip(img, 1)

        # 1. Face Detection
        # findFaceMesh returns the image and a list of all landmark lists (one for each face)
        img, faces = detector.findFaceMesh(img, draw=False)

        info_text = "Status: Card hidden (No face detected)"
        current_card_img = original_card_img.copy()

        if faces:
            # We focus on the first detected face's landmark list (468 points)
            lmList = faces[0]

            # --- Forehead Calculation ---
            # Landmark 10 is typically the top-center of the head/forehead.
            current_forehead_center = lmList[10]
            current_x, current_y = (
                current_forehead_center[0],
                current_forehead_center[1],
            )

            # Apply Exponential Moving Average (EMA) to smooth the position
            global _smooth_forehead_x, _smooth_forehead_y
            if _smooth_forehead_x == 0 and _smooth_forehead_y == 0:
                _smooth_forehead_x = current_x
                _smooth_forehead_y = current_y
            else:
                _smooth_forehead_x = (COORDINATE_SMOOTHING_ALPHA * current_x) + (
                    (1 - COORDINATE_SMOOTHING_ALPHA) * _smooth_forehead_x
                )
                _smooth_forehead_y = (COORDINATE_SMOOTHING_ALPHA * current_y) + (
                    (1 - COORDINATE_SMOOTHING_ALPHA) * _smooth_forehead_y
                )

            smoothed_forehead_center = (
                int(_smooth_forehead_x),
                int(_smooth_forehead_y),
            )

            # Calculate face bounding box manually for sizing reference
            x_coords = [p[0] for p in lmList]
            y_coords = [p[1] for p in lmList]
            x_min, x_max = min(x_coords), max(x_coords)
            face_w = x_max - x_min
            # --------------------------

            # 2. Glitch Logic: Check timing and update active states
            glitch.scheduler()

            # 3. Dynamic Opacity and Glitch Application
            if glitch.is_any_glitch_running():
                current_card_img = glitch.apply(current_card_img)
                current_opacity = GLITCH_OPACITY
                info_text = (
                    f"Status: Card STUCK ({current_opacity * 100:.0f}%) - GLITCH ACTIVE"
                )
            else:
                current_opacity = DEFAULT_OPACITY
                info_text = f"Status: Card STUCK ({current_opacity * 100:.0f}%)"

            # 4. Overlay the card using the smoothed position
            img = overlay_card_on_forehead(
                img, current_card_img, smoothed_forehead_center, face_w, current_opacity
            )

        # 5. Display Information and Frame
        # Combine status text and FPS text
        full_status_text = f"{info_text} | {fps_text}"
        draw_info_box(img, full_status_text, 10, FRAME_HEIGHT - 10)

        cv2.imshow("Demo Stick Card Forehead", img)

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
