# File: asimov/interactive_grid.py
# File: asimov/interactive_grid.py

import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from asimov.common import safe_distance

# -----------------------------
# Named constants
# -----------------------------
DEFAULT_ROWS = 2
DEFAULT_COLS = 2

CELL_COLOR = (200, 200, 200)       # unselected cell color
HOVER_COLOR = (180, 180, 250)      # hover visual
SELECTED_COLOR = (0, 255, 0)       # selected cell color
PINCH_COLOR = (0, 255, 255)        # pinch highlight

UNSELECTED_ALPHA = 0.4
SELECTED_ALPHA = 0.8
PINCH_ALPHA = 0.6

TOP_MARGIN_PCT = 0.05      # smaller top margin
BOTTOM_MARGIN_PCT = 0.1
LEFT_MARGIN_PCT = 0.05     # smaller left margin
RIGHT_MARGIN_PCT = 0.1

PINCH_DISTANCE_THRESHOLD = 40

# Index-only gesture array: [thumb, index, middle, ring, pinky]
INDEX_ONLY_GESTURE = [False, True, False, False, False]

# Default frame size (can be overridden in constructor)
DEFAULT_FRAME_WIDTH = 1024
DEFAULT_FRAME_HEIGHT = 768

class InteractiveGrid:
    def __init__(self, rows=DEFAULT_ROWS, cols=DEFAULT_COLS,
                 singleton_selection=False, frame_width=1024, frame_height=768):
        self.rows = rows
        self.cols = cols
        self.singleton_selection = singleton_selection
        self.frame_width = frame_width
        self.frame_height = frame_height

        self.hover_cell = None
        self.selected_cells = set()
        self.pinch_cell = None
        self.pinch_active = False
        # Hand detector
        self.detector = HandDetector(maxHands=1, detectionCon=0.8)

    def update(self, frame, mouse_pos=None, mouse_clicked=False):
        """Update hover, selection, and pinch based on input."""
        hands, _ = self.detector.findHands(frame, draw=False)

        # Reset hover by default
        self.hover_cell = None
        self.pinch_cell = None

        # -----------------------------
        # Process hand input
        # -----------------------------
        if hands:
            hand = hands[0]
            lmList = hand["lmList"]
            fingers = self.detector.fingersUp(hand)
            index_tip = lmList[8]
            thumb_tip = lmList[4]
            px, py = int(index_tip[0]), int(index_tip[1])

            # Hover: only index finger extended, visual only
            if fingers == INDEX_ONLY_GESTURE:
                self.hover_cell = self.get_cell_from_position(px, py)

            # --- Pinch selection (thumb + index must be extended and close together) ---
            if fingers[0] == 1 and fingers[1] == 1:
                dist = safe_distance(index_tip, thumb_tip)
                pinch_now = dist < PINCH_DISTANCE_THRESHOLD

                if pinch_now and not self._pinch_active:
                    # Determine which cell we're pinching over
                    cell = self.get_cell_from_position(px, py)
                    if cell is not None:
                        # Toggle the cell state explicitly
                        if cell in self.selected_cells:
                            self.selected_cells.remove(cell)
                        else:
                            self._select_cell(cell)

                # Update pinch state
                self._pinch_active = pinch_now

        # -----------------------------
        # Mouse input
        # -----------------------------
        if mouse_pos is not None:
            if self.hover_cell is None:
                self.hover_cell = self.get_cell_from_position(mouse_pos[0], mouse_pos[1])

        if mouse_clicked and mouse_pos is not None:
            cell = self.get_cell_from_position(mouse_pos[0], mouse_pos[1])
            self._select_cell(cell)

        # Draw hands on top
        if hands:
            self._draw_hands(frame, hands)

    # -----------------------------
    # Selection helper
    # -----------------------------
    def _select_cell(self, cell):
        if cell is None:
            return
        if self.singleton_selection:
            self.selected_cells = {cell}
        else:
            if cell in self.selected_cells:
                self.selected_cells.remove(cell)
            else:
                self.selected_cells.add(cell)

    # -----------------------------
    # Draw grid
    # -----------------------------
    def draw_grid(self, frame):
        x0 = int(self.frame_width * LEFT_MARGIN_PCT)
        x1 = int(self.frame_width * (1 - RIGHT_MARGIN_PCT))
        y0 = int(self.frame_height * TOP_MARGIN_PCT)
        y1 = int(self.frame_height * (1 - BOTTOM_MARGIN_PCT))

        grid_w = x1 - x0
        grid_h = y1 - y0
        cell_w = grid_w / self.cols
        cell_h = grid_h / self.rows

        overlay = frame.copy()
        for r in range(self.rows):
            for c in range(self.cols):
                cell_x0 = int(x0 + c * cell_w)
                cell_y0 = int(y0 + r * cell_h)
                cell_x1 = int(cell_x0 + cell_w)
                cell_y1 = int(cell_y0 + cell_h)

                color = CELL_COLOR
                alpha = UNSELECTED_ALPHA
                cell_idx = (r, c)

                if cell_idx in self.selected_cells:
                    color = SELECTED_COLOR
                    alpha = SELECTED_ALPHA
                elif cell_idx == self.hover_cell:
                    color = HOVER_COLOR
                    alpha = UNSELECTED_ALPHA  # lighter, only visual
                elif cell_idx == self.pinch_cell:
                    color = PINCH_COLOR
                    alpha = PINCH_ALPHA

                cv2.rectangle(overlay, (cell_x0, cell_y0), (cell_x1, cell_y1), color, -1)
                frame[cell_y0:cell_y1, cell_x0:cell_x1] = cv2.addWeighted(
                    overlay[cell_y0:cell_y1, cell_x0:cell_x1], alpha,
                    frame[cell_y0:cell_y1, cell_x0:cell_x1], 1 - alpha, 0
                )
                cv2.rectangle(frame, (cell_x0, cell_y0), (cell_x1, cell_y1), (50, 50, 50), 2)

    # -----------------------------
    # Helpers
    # -----------------------------
    def get_cell_from_position(self, px, py):
        if px is None or py is None:
            return None
        x0 = int(self.frame_width * LEFT_MARGIN_PCT)
        x1 = int(self.frame_width * (1 - RIGHT_MARGIN_PCT))
        y0 = int(self.frame_height * TOP_MARGIN_PCT)
        y1 = int(self.frame_height * (1 - BOTTOM_MARGIN_PCT))

        grid_w = x1 - x0
        grid_h = y1 - y0

        if not (x0 <= px <= x1 and y0 <= py <= y1):
            return None

        col = int((px - x0) // (grid_w / self.cols))
        row = int((py - y0) // (grid_h / self.rows))
        return (row, col)

    def _draw_hands(self, frame, hands):
        for hand in hands:
            lmList = hand["lmList"]
            for x, y, z in lmList:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
