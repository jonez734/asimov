import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector


class InteractiveGrid:
    def __init__(self, items, cols=4, frame_size=(600, 400),
                 cell_size=(100, 100), padding=10, detection_conf=0.8):
        self.items = items
        self.cols = cols
        self.rows = (len(items) + cols - 1) // cols
        self.frame_size = frame_size
        self.cell_size = cell_size
        self.padding = padding

        self.cell_positions = self._compute_cell_positions()
        self.hover_idx = None
        self.detector = HandDetector(detectionCon=detection_conf, maxHands=1)
        self.last_click = False

    def _compute_cell_positions(self):
        positions = []
        for idx, _ in enumerate(self.items):
            row = idx // self.cols
            col = idx % self.cols
            x = self.padding + col * (self.cell_size[0] + self.padding)
            y = self.padding + row * (self.cell_size[1] + self.padding)
            positions.append((x, y))
        return positions

    def _get_idx_at_pos(self, pos):
        x, y = pos
        for idx, (cx, cy) in enumerate(self.cell_positions):
            if cx <= x <= cx + self.cell_size[0] and cy <= y <= cy + self.cell_size[1]:
                return idx
        return None

    def update_hover_and_click(self, frame):
        hands = self.detector.findHands(frame, draw=False)
        self.hover_idx = None
        clicked_item = None

        if hands:
            hand = hands[0]
            lmList = hand['lmList']
            index_tip = lmList[8]
            thumb_tip = lmList[4]

            x, y = int(index_tip[0]), int(index_tip[1])
            self.hover_idx = self._get_idx_at_pos((x, y))

            distance = np.linalg.norm(np.array(thumb_tip[:2]) - np.array(index_tip[:2]))
            click = distance < 40

            if click and not self.last_click and self.hover_idx is not None:
                clicked_item = self.items[self.hover_idx]
            self.last_click = click
        else:
            self.last_click = False

        return clicked_item

    def draw(self, frame, alpha=1.0):
        overlay = frame.copy()
        for idx, item in enumerate(self.items):
            x, y = self.cell_positions[idx]
            color = (100, 100, 100)
            if idx == self.hover_idx:
                color = (50, 150, 255)

            cv2.rectangle(overlay, (x, y),
                          (x + self.cell_size[0],_
