import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from asimov.interactive_grid import InteractiveGrid

# Suits and ranks
SUITS = ['C', 'D', 'S', 'H']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


class TwoPhaseGridDemo:
    def __init__(self, frame_size=(1280, 720)):
        self.frame_w, self.frame_h = frame_size
        self.phase = 'suits'  # 'suits', 'ranks', 'transition'
        self.next_phase = None
        self.selected_suit = None

        # Initialize grids
        self.suit_grid = InteractiveGrid(
            items=SUITS,
            rows=1,
            cols=4,
            cell_size=(200, 200),
            margin=40,
            alpha=0.6,
            frame_size=frame_size
        )
        self.rank_grid = None

        # Transition alpha
        self.transition_alpha = 0.0
        self.transition_speed = 0.08

    def start_transition(self, to_phase):
        self.next_phase = to_phase
        self.transition_alpha = 0.0
        self.phase = 'transition'

    def update_transition(self):
        self.transition_alpha += self.transition_speed
        if self.transition_alpha >= 1.0:
            self.phase = self.next_phase
            self.next_phase = None
            self.transition_alpha = 0.0

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(3, self.frame_w)
        cap.set(4, self.frame_h)

        detector = HandDetector(detectionCon=0.8, maxHands=1)

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            base = frame.copy()

            # Draw suit grid always in background
            self.suit_grid.draw(base)

            hands, _ = detector.findHands(frame, draw=False)
            cx, cy = None, None
            if hands:
                hand = hands[0]
                lmList = hand['lmList']
                cx, cy = hand['center']

            # Phase logic
            if self.phase == 'suits':
                clicked = None
                if hands:
                    self.suit_grid.update_selection(cx, cy)
                    distance = np.linalg.norm(np.array(lmList[4][:2]) - np.array(lmList[8][:2]))
                    if distance < 40 and self.suit_grid.active_index is not None:
                        clicked = self.suit_grid.active_index

                if clicked is not None:
                    self.selected_suit = SUITS[clicked]
                    # Create rank grid
                    cols = min(len(RANKS), 6)
                    rows = (len(RANKS) + cols - 1) // cols
                    self.rank_grid = InteractiveGrid(
                        items=RANKS,
                        rows=rows,
                        cols=cols,
                        cell_size=(150, 150),
                        margin=20,
                        alpha=0.6,
                        frame_size=(self.frame_w, self.frame_h)
                    )
                    self.start_transition('ranks')

            elif self.phase == 'ranks' and self.rank_grid:
                clicked = None
                if hands:
                    self.rank_grid.update_selection(cx, cy)
                    distance = np.linalg.norm(np.array(lmList[4][:2]) - np.array(lmList[8][:2]))
                    if distance < 40 and self.rank_grid.active_index is not None:
                        clicked = self.rank_grid.active_index

                if clicked is not None:
                    selected_rank = RANKS[clicked]
                    print(f"Selected card: {self.selected_suit}{selected_rank}")
                    self.rank_grid = None
                    self.start_transition('suits')

            elif self.phase == 'transition':
                if self.next_phase == 'ranks' and self.rank_grid:
                    self.rank_grid.draw(base, alpha=self.transition_alpha)
                elif self.next_phase == 'suits' and self.rank_grid:
                    self.rank_grid.draw(base, alpha=1 - self.transition_alpha)
                self.update_transition()

            cv2.imshow("Two-Phase InteractiveGrid", base)
            if cv2.waitKey(1) & 0xFF == 27:
                break

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    TwoPhaseGridDemo().run()
