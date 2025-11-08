import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector

class InteractiveGrid:
    def __init__(self, rows, cols, on_touch, labels=None,
                 margin_ratio=0.05,
                 base_color=(40, 40, 40),
                 hover_color=(100, 200, 255),
                 touched_color=(0, 255, 0)):
        """
        rows, cols: grid dimensions
        on_touch: callback(index, rect)
        margin_ratio: fraction of width/height used for margins
        """
        self.rows = rows
        self.cols = cols
        self.on_touch = on_touch
        self.labels = labels# or [f"{r},{c}" for r in range(rows) for c in range(cols)]
        self.margin_ratio = margin_ratio
        self.base_color = np.array(base_color, dtype=np.float32)
        self.hover_color = np.array(hover_color, dtype=np.float32)
        self.touched_color = np.array(touched_color, dtype=np.float32)

        self.rects = []
        self.hover_index = None
        self.detector = HandDetector(detectionCon=0.8, maxHands=1)

        # animation state
        self.scale_factor = 1.0  # [0,1] — initial size of boxes
        self.alpha = 0.0         # [0,1] — fade-in opacity

    # ------------------------------------------------------------------

    def layout_rects(self, frame_shape):
        h, w, _ = frame_shape
        total_w = int(w * 0.8 * self.scale_factor)
        total_h = int(h * 0.8 * self.scale_factor)

        box_w = total_w // self.cols
        box_h = total_h // self.rows

        start_x = (w - total_w) // 2
        start_y = (h - total_h) // 2

        self.rects = []
        label_count = len(self.labels)
        expected = self.rows * self.cols

        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                x1 = start_x + c * box_w
                y1 = start_y + r * box_h
                x2 = x1 + box_w
                y2 = y1 + box_h

                # If labels list is too short, fall back gracefully
                label = self.labels[idx] if idx < label_count else f"{r},{c}"
                self.rects.append(((x1, y1, x2, y2), label))

        if label_count != expected:
            print(f"[WARN] Expected {expected} labels, got {label_count}. Using fallbacks for extras.")
    # ------------------------------------------------------------------
    def update(self, frame):
        """
        Update the grid state: hover detection and touch detection.

        - Detect hands with draw=False
        - Update self.hover_index based on single index finger hover
        - Trigger self.on_touch() if both index and middle fingers up
        - Returns the frame (not drawn on)
        """
        hands, frame = self.detector.findHands(frame, draw=False)
        self.hover_index = None

        for hand in hands:
            fingers = self.detector.fingersUp(hand)
            ix, iy = hand['lmList'][8][:2]  # Index fingertip

            # Check for hover (single index finger up)
            if fingers[1] == 1 and sum(fingers) == 1:
                for i, (rect, _) in enumerate(self.rects):
                    x1, y1, x2, y2 = rect
                    if x1 <= ix <= x2 and y1 <= iy <= y2:
                        self.hover_index = i
                        break

            # Check for touch (index + middle fingers up)
            if fingers[1] == 1 and fingers[2] == 1:
                for i, (rect, _) in enumerate(self.rects):
                    x1, y1, x2, y2 = rect
                    if x1 <= ix <= x2 and y1 <= iy <= y2:
                        if callable(self.on_touch):
                            self.on_touch(i, rect)
                        break

        return frame

    # ------------------------------------------------------------------

    def draw_rectangles(self, frame):
        """Draw grid boxes with fade-in background and opaque borders.
           Default border is blue; hover border is green.
        """
        # prepare overlay for backgrounds
        overlay = frame.copy().astype(np.float32)

        for i, (rect, _) in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            if x2 <= x1 or y2 <= y1:
                continue

            # Fill (background) color
            fill_color = self.hover_color if i == self.hover_index else self.base_color
            cv2.rectangle(overlay, (x1, y1), (x2, y2), fill_color.tolist(), cv2.FILLED)

            # draw thin inner stroke on overlay so shape edges blend naturally (optional)
            cv2.rectangle(overlay, (x1+2, y1+2), (x2-2, y2-2), (255,255,255), 1)

        # Blend overlay backgrounds with the frame using fade alpha
        blended = np.empty_like(frame, dtype=np.float32)
        cv2.addWeighted(overlay, self.alpha, frame.astype(np.float32), 1 - self.alpha, 0, blended)

        # Convert to uint8 to draw final opaque borders and labels
        out = blended.astype(np.uint8)

        # Draw opaque borders on top: blue normally, green on hover
        for i, (rect, _) in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            if x2 <= x1 or y2 <= y1:
                continue
            border_color = (0, 255, 0) if i == self.hover_index else (255, 0, 0)  # green on hover, blue default
            cv2.rectangle(out, (x1, y1), (x2, y2), border_color, 3)

        return out

    # ------------------------------------------------------------------

    def draw_labels(self, frame):
        """Draw text labels separately (after rectangles)."""
        for i, (rect, label) in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            text_pos = (x1 + 10, y1 + 40)
            cv2.putText(frame, label, text_pos, cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 255, 255), 2)
        return frame

    # ------------------------------------------------------------------

    def animate_in(self, scale_step=0.03, alpha_step=0.05):
        """Incrementally animate scale and fade-in."""
        changed = False
        if self.scale_factor < 1.0:
            self.scale_factor = min(1.0, self.scale_factor + scale_step)
            changed = True
        if self.alpha < 0.50:
            self.alpha = min(0.50, self.alpha + alpha_step)
            changed = True
        return changed


# ----------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------

def on_touch(index, rect):
    print(f"Touched rectangle {index} at {rect}")


def main():
    cap = cv2.VideoCapture(0)
    ok, frame = cap.read()
    if not ok:
        print("No camera.")
        return

    frame = cv2.flip(frame, 1)  # Mirror the image horizontally

    # -----------------------------
    # Define labels before creating the grid
    # -----------------------------
    suits = ['C', 'D', 'H', 'S']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    rows, cols = 5, 5
    labels = suits + ranks[:rows*cols - len(suits)]  # top 4 = suits, rest = ranks

    grid = InteractiveGrid(rows=rows, cols=cols, on_touch=on_touch, labels=labels)
    grid.scale_factor = 0.0
    grid.alpha = 0.0
    grid.layout_rects(frame.shape)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Run animation if not complete
        if grid.animate_in(scale_step=0.02, alpha_step=0.03):
            grid.layout_rects(frame.shape)

        frame = grid.update(frame)
        frame = grid.draw_rectangles(frame)
        frame = grid.draw_labels(frame)

        hands, frame = grid.detector.findHands(frame, draw=True)

        cv2.imshow("Interactive Grid Demo", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
