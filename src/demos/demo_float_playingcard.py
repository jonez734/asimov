import argparse

import cv2
from cvzone.HandTrackingModule import HandDetector
from asimov.playingcard.util import compute_geometry
from asimov.playingcard import load  as load_card
from asimov import conf

# from asimov.rect import detect_from_frame  # example rect detection function

# -------------------------
# CONFIGURATION
# -------------------------
CARD_BORDER = 0.25   # minimum border ratio
CARD_FILE = "ace_of_spades.png"  # example PNG


# Landmark indices (cvzone uses 0-20)
THUMB_TIP = 4
INDEX_FINGER_TIP = 8
MIDDLE_FINGER_TIP = 12
RING_FINGER_TIP = 16
PINKY_TIP = 20
THUMB_CMC = 1
INDEX_FINGER_MCP = 5
MIDDLE_FINGER_MCP = 9
RING_FINGER_MCP = 13
PINKY_MCP = 17

# Initialize cvzone HandDetector
hands_detector = HandDetector(detectionCon=0.7, maxHands=1)


def is_fist(hand_landmarks, frame_h):
    """
    Returns True if the hand appears closed (fist). 
    hand_landmarks: cvzone lmList (list of [x, y, z] coordinates)
    frame_h: frame height (for scaling y coords)
    """
    tips = [
        THUMB_TIP,
        INDEX_FINGER_TIP,
        MIDDLE_FINGER_TIP,
        RING_FINGER_TIP,
        PINKY_TIP,
    ]
    mcps = [
        THUMB_CMC,
        INDEX_FINGER_MCP,
        MIDDLE_FINGER_MCP,
        RING_FINGER_MCP,
        PINKY_MCP,
    ]

    closed_count = 0
    for tip, mcp in zip(tips, mcps):
        tip_y = hand_landmarks[tip][1]
        mcp_y = hand_landmarks[mcp][1]
        if tip_y > mcp_y:
            closed_count += 1

    return closed_count >= 5

def detect_hand(frame):
    """
    Detects hand(s) in a frame and returns a list of rect-like objects:
      rect.x, rect.y, rect.width, rect.height
    Optimized for real-time performance.
    """
    hands, frame = hands_detector.findHands(frame, draw=False)
    rects = []

    if hands:
        for hand in hands:
            if is_fist(hand["lmList"], frame.shape[0]):
                continue

            lmList = hand["lmList"]
            xs = [lm[0] for lm in lmList]
            ys = [lm[1] for lm in lmList]
            x1, x2 = int(min(xs)), int(max(xs))
            y1, y2 = int(min(ys)), int(max(ys))

            rect = type("Rect", (), {})()
            rect.x = x1
            rect.y = y1
            rect.width = x2 - x1
            rect.height = y2 - y1
            rects.append(rect)

    return rects

# -------------------------
# UTILS
# -------------------------
def overlay_png(frame, png, x, y, w, h):
    """Alpha blend a PNG into frame at (x, y) with size (w, h)."""
    if png.shape[2] == 4:
        # resize
        resized = cv2.resize(png, (w, h), interpolation=cv2.INTER_AREA)
        alpha = resized[:, :, 3:4].astype(float) / 255.0
        rgb = resized[:, :, :3].astype(float)
        dest = frame[y:y+h, x:x+w].astype(float)
        blended = alpha * rgb + (1.0 - alpha) * dest
        frame[y:y+h, x:x+w] = blended.astype(frame.dtype)
    else:
        frame[y:y+h, x:x+w] = cv2.resize(png, (w, h), interpolation=cv2.INTER_AREA)

# -------------------------
# MAIN
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Floating playing card demo")
    parser.add_argument("--device", type=int, default=conf.CAP_DEVICE, help="Camera device index")
    parser.add_argument("--card", type=str, required=True, help="Card PNG filename to load")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.device)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    card_image = load_card(args.card)
    if card_image is None:
        print(f"Failed to load {CARD_FILE}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rects = detect_hand(frame)

        for card_rect in rects:
            # compute geometry inside this rect
            fw, fh = card_rect.width, card_rect.height
            png_h, png_w = card_image.shape[:2]

            rel_x, rel_y, rw, rh = compute_geometry(
                fw, fh, png_w, png_h, border_ratio=CARD_BORDER
            )

            draw_x = card_rect.x + rel_x
            draw_y = card_rect.y + rel_y

            # clamp to frame bounds
            end_x = min(draw_x + rw, frame.shape[1])
            end_y = min(draw_y + rh, frame.shape[0])
            rw = end_x - draw_x
            rh = end_y - draw_y
            if rw > 0 and rh > 0:
                overlay_png(frame, card_image, draw_x, draw_y, rw, rh)

        cv2.imshow("Card Demo", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC to quit
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
