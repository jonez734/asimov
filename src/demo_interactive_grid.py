import cv2
import time
from cvzone.HandTrackingModule import HandDetector
from asimov.interactive_grid import InteractiveGrid
from asimov.common import safe_distance  # safe distance utility

# ----------------------------
# Constants
# ----------------------------
SUITS = ["H", "C", "D", "S"]
RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

# ----------------------------
# Demo Class
# ----------------------------
class TwoPhaseGridDemo:
    def __init__(self):
        # Camera
        self.cap = cv2.VideoCapture(0)
        self.width, self.height = 1280, 720
        self.cap.set(3, self.width)
        self.cap.set(4, self.height)

        # Hand detector
        self.detector = HandDetector(detectionCon=0.8, maxHands=1)

        # Grids
        self.suit_grid = InteractiveGrid(SUITS, cols=4, rows=1)
        self.rank_grid = None

        # State
        self.phase = "suits"  # suits -> ranks
        self.selected_suit = None
        self.transition_alpha = 0.0
        self.transition_dir = None
        self.transition_start = None
        self.transition_duration = 0.5  # seconds
        self.pinching = False

    # ----------------------------
    # Transition helpers
    # ----------------------------
    def start_transition(self, target_phase):
        self.transition_dir = target_phase
        self.transition_alpha = 0.0
        self.transition_start = time.time()

    def update_transition(self):
        if self.transition_dir is None:
            return False
        elapsed = time.time() - self.transition_start
        t = min(1.0, elapsed / self.transition_duration)
        self.transition_alpha = t
        if t >= 1.0:
            self.phase = self.transition_dir
            self.transition_dir = None
            self.transition_alpha = 0.0
        return True

    # ----------------------------
    # Main loop
    # ----------------------------
    def run(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)

            # Hand detection
            hands, frame = self.detector.findHands(frame, flipType=False)

            # ------------------------
            # Pinch detection
            # ------------------------
            pinch_detected = False
            if hands:
                lmList = hands[0]["lmList"]
                distance = safe_distance(lmList[4], lmList[8])
                if distance is not None:
                    if distance < 40 and not self.pinching:
                        pinch_detected = True
                        self.pinching = True
                    elif distance >= 40:
                        self.pinching = False
            else:
                self.pinching = False

            # ------------------------
            # Handle transition
            # ------------------------
            transitioning = self.update_transition()
            overlay = frame.copy()

            # ------------------------
            # Phase logic
            # ------------------------
            if self.phase == "suits":
                self.suit_grid.animate_in()
                self.suit_grid.draw(overlay, hands)

                if pinch_detected and self.suit_grid.active_index is not None:
                    self.selected_suit = SUITS[self.suit_grid.active_index]
                    print(f"Selected suit: {self.selected_suit}")
                    self.rank_grid = InteractiveGrid(RANKS, cols=7, rows=2)
                    self.start_transition("ranks")

            elif self.phase == "ranks":
                if self.rank_grid is None:
                    continue
                self.rank_grid.animate_in()
                self.rank_grid.draw(overlay, hands)

                if pinch_detected and self.rank_grid.active_index is not None:
                    selected_rank = RANKS[self.rank_grid.active_index]
                    print(f"Selected card: {selected_rank} of {self.selected_suit}")
                    self.rank_grid = None
                    self.start_transition("suits")

            # ------------------------
            # Alpha blending
            # ------------------------
            if transitioning:
                alpha = self.transition_alpha
                frame = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)
            else:
                frame = overlay

            # Display
            cv2.imshow("Two-Phase Grid Demo", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break

        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()


# ----------------------------
# Run the demo
# ----------------------------
if __name__ == "__main__":
    TwoPhaseGridDemo().run()
