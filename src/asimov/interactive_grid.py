# File: interactive_grid.py

import cv2
from asimov.common import safe_distance

# -----------------------------
# Named constants
# -----------------------------
DEFAULT_ROWS = 2
DEFAULT_COLS = 2
DEFAULT_CELL_COLOR = (200, 200, 200)      # light gray
HOVER_COLOR = (255, 255, 0)               # yellow
SELECTED_COLOR = (0, 255, 0)              # green
PINCH_COLOR = (255, 0, 0)                 # red
CELL_ALPHA = 0.4
HOVER_ALPHA = 0.6
SELECTED_ALPHA = 0.8
PINCH_ALPHA = 0.8
TOP_MARGIN = 0.1      # percentage
BOTTOM_MARGIN = 0.1
LEFT_MARGIN = 0.1
RIGHT_MARGIN = 0.1

INDEX_ONLY_GESTURE = [False, True, False, False, False]
PINCH_DISTANCE_THRESHOLD = 40  # pixels

class InteractiveGrid:
    def __init__(self, rows=DEFAULT_ROWS, cols=DEFAULT_COLS, singleton_selection=False):
        self.rows = rows
        self.cols = cols
        self.singleton_selection = singleton_selection
        self.hover_cell = None
        self.selected_cells = set()
        self.pinch_cell = None

    # -----------------------------
    # Cell / grid helpers
    # -----------------------------
    def get_cell_rect(self, row, col, frame_w, frame_h):
        """Return (x0, y0, x1, y1) pixel rectangle for a cell"""
        x0 = int(frame_w * LEFT_MARGIN + col * (frame_w * (1 - LEFT_MARGIN - RIGHT_MARGIN) / self.cols))
        x1 = int(frame_w * LEFT_MARGIN + (col + 1) * (frame_w * (1 - LEFT_MARGIN - RIGHT_MARGIN) / self.cols))
        y0 = int(frame_h * TOP_MARGIN + row * (frame_h * (1 - TOP_MARGIN - BOTTOM_MARGIN) / self.rows))
        y1 = int(frame_h * TOP_MARGIN + (row + 1) * (frame_h * (1 - TOP_MARGIN - BOTTOM_MARGIN) / self.rows))
        return x0, y0, x1, y1

    def get_cell_from_position(self, px, py, frame_w=1, frame_h=1):
        """Return (row, col) given a pixel position, or None if out of bounds"""
        if px is None or py is None:
            return None

        for row in range(self.rows):
            for col in range(self.cols):
                x0, y0, x1, y1 = self.get_cell_rect(row, col, frame_w, frame_h)
                if x0 <= px <= x1 and y0 <= py <= y1:
                    return row, col
        return None

    # -----------------------------
    # Hover / selection / pinch
    # -----------------------------
    def update_hover_by_position(self, px, py, frame_w=1, frame_h=1):
        """Update hover cell, None clears hover"""
        if px is None or py is None:
            self.hover_cell = None
            return
        cell = self.get_cell_from_position(px, py, frame_w, frame_h)
        self.hover_cell = cell

    def attempt_select(self, fingers, px, py, frame_w=1, frame_h=1):
        """Select cell if gesture matches INDEX_ONLY_GESTURE"""
        if fingers == INDEX_ONLY_GESTURE:
            cell = self.get_cell_from_position(px, py, frame_w, frame_h)
            if cell is None:
                return
            if self.singleton_selection:
                self.selected_cells = {cell}
            else:
                self.selected_cells.add(cell)

    def update_pinch_by_distance(self, dist):
        """Set pinch cell based on distance threshold"""
        if dist is not None and dist < PINCH_DISTANCE_THRESHOLD:
            self.pinch_cell = True
        else:
            self.pinch_cell = None

    # -----------------------------
    # Draw grid
    # -----------------------------
    def draw_grid(self, frame):
        h, w = frame.shape[:2]
        for row in range(self.rows):
            for col in range(self.cols):
                x0, y0, x1, y1 = self.get_cell_rect(row, col, w, h)
                alpha = CELL_ALPHA
                color = DEFAULT_CELL_COLOR

                if (row, col) == self.hover_cell:
                    alpha = HOVER_ALPHA
                    color = HOVER_COLOR
                if (row, col) in self.selected_cells:
                    alpha = SELECTED_ALPHA
                    color = SELECTED_COLOR
                if self.pinch_cell and (row, col) == self.hover_cell:
                    alpha = PINCH_ALPHA
                    color = PINCH_COLOR

                overlay = frame.copy()
                cv2.rectangle(overlay, (x0, y0), (x1, y1), color, -1)
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        return frame
