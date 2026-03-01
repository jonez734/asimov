# File: asimov/interactive_grid.py

import cv2

# ======================
# Constants / Parameters
# ======================

CELL_COLOR = (0, 255, 0)
HOVER_COLOR = (0, 255, 255)
SELECTED_COLOR = (0, 200, 0)
PINCH_COLOR = (255, 0, 255)

# Transparency levels
CELL_ALPHA = 0.4
HOVER_ALPHA = 0.5
SELECTED_ALPHA = 0.7
PINCH_ALPHA = 0.8

# Grid size defaults
DEFAULT_ROWS = 2
DEFAULT_COLS = 2
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480

# Grid margins as percentage of frame
CELL_TOP_MARGIN_PCT = 0.1
CELL_BOTTOM_MARGIN_PCT = 0.1
CELL_LEFT_MARGIN_PCT = 0.1
CELL_RIGHT_MARGIN_PCT = 0.1

# Label margins within each cell (percent of cell)
LABEL_TOP_MARGIN_PCT = 0.1
LABEL_BOTTOM_MARGIN_PCT = 0.1
LABEL_LEFT_MARGIN_PCT = 0.1
LABEL_RIGHT_MARGIN_PCT = 0.1

# Text appearance
LABEL_FONT = cv2.FONT_HERSHEY_SIMPLEX
LABEL_FONT_SCALE = 0.6
LABEL_THICKNESS = 1
LABEL_COLOR = (255, 255, 255)

# Distance thresholds for pinch gesture
PINCH_DISTANCE_THRESH = 40


class InteractiveGrid:
    """Interactive grid supporting mouse and hand gestures with full features."""

    def __init__(
        self,
        rows=DEFAULT_ROWS,
        cols=DEFAULT_COLS,
        singleton_selection=False,
        frame_width=DEFAULT_WIDTH,
        frame_height=DEFAULT_HEIGHT,
    ):
        self.rows = rows
        self.cols = cols
        self.singleton_selection = singleton_selection
        self.frame_width = frame_width
        self.frame_height = frame_height

        self.selected = [[False for _ in range(cols)] for _ in range(rows)]
        self.hovered = [[False for _ in range(cols)] for _ in range(rows)]
        self.pinch_active = False
        self.last_hover = None

    # =====================
    # Layout / Cell helpers
    # =====================

    def _compute_grid_layout(self, frame_width, frame_height):
        left_px = int(round(frame_width * CELL_LEFT_MARGIN_PCT))
        right_px = int(round(frame_width * CELL_RIGHT_MARGIN_PCT))
        top_px = int(round(frame_height * CELL_TOP_MARGIN_PCT))
        bottom_px = int(round(frame_height * CELL_BOTTOM_MARGIN_PCT))

        grid_w = frame_width - left_px - right_px
        grid_h = frame_height - top_px - bottom_px

        # Integer-safe
        base_col_w = grid_w // self.cols
        rem_w = grid_w % self.cols
        col_widths = [base_col_w + (1 if i < rem_w else 0) for i in range(self.cols)]

        base_row_h = grid_h // self.rows
        rem_h = grid_h % self.rows
        row_heights = [base_row_h + (1 if i < rem_h else 0) for i in range(self.rows)]

        return left_px, top_px, col_widths, row_heights

    def get_cell_rect(self, row, col, frame_width=None, frame_height=None):
        if frame_width is None:
            frame_width = self.frame_width
        if frame_height is None:
            frame_height = self.frame_height

        left_px, top_px, col_widths, row_heights = self._compute_grid_layout(frame_width, frame_height)
        x = left_px + sum(col_widths[:col])
        y = top_px + sum(row_heights[:row])
        w = col_widths[col]
        h = row_heights[row]

        # Clamp to frame
        if x + w > frame_width:
            w = frame_width - x
        if y + h > frame_height:
            h = frame_height - y
        return x, y, w, h

    def get_cell_from_position(self, px, py, frame_width=None, frame_height=None):
        if px is None or py is None:
            return None
        if frame_width is None:
            frame_width = self.frame_width
        if frame_height is None:
            frame_height = self.frame_height

        left_px, top_px, col_widths, row_heights = self._compute_grid_layout(frame_width, frame_height)
        grid_left = left_px
        grid_top = top_px
        grid_right = left_px + sum(col_widths)
        grid_bottom = top_px + sum(row_heights)

        if not (grid_left <= px < grid_right and grid_top <= py < grid_bottom):
            return None

        cx = px - grid_left
        cy = py - grid_top

        col = 0
        acc = 0
        for i, w in enumerate(col_widths):
            acc += w
            if cx < acc:
                col = i
                break

        row = 0
        acc = 0
        for i, h in enumerate(row_heights):
            acc += h
            if cy < acc:
                row = i
                break

        return row, col

    # ======================
    # Hover and selection
    # ======================

    def update_hover_by_position(self, px, py, frame_width=None, frame_height=None):
        for r in range(self.rows):
            for c in range(self.cols):
                self.hovered[r][c] = False

        result = self.get_cell_from_position(px, py, frame_width, frame_height)
        if result is not None:
            r, c = result
            self.hovered[r][c] = True
            self.last_hover = (r, c)
        else:
            self.last_hover = None

    def attempt_select(self, gesture_type, px, py, frame_width=None, frame_height=None):
        result = self.get_cell_from_position(px, py, frame_width, frame_height)
        if result is None:
            return
        row, col = result
        if self.singleton_selection:
            for r in range(self.rows):
                for c in range(self.cols):
                    self.selected[r][c] = False
        self.selected[row][col] = not self.selected[row][col]

    def update_pinch_by_position(self, px, py, pinch_active, frame_width=None, frame_height=None):
        result = self.get_cell_from_position(px, py, frame_width, frame_height)
        if result is None:
            return
        row, col = result
        if pinch_active:
            self.selected[row][col] = not self.selected[row][col]

    # =========================
    # Unified update for demo
    # =========================

    def update(self, frame, cursor_pos=None, click=False, pinch_pos=None, pinch_active=False):
        """Update hover and selection for mouse and hand input."""
        h, w = frame.shape[:2]

        # Hover by mouse
        if cursor_pos is not None:
            px, py = cursor_pos
            self.update_hover_by_position(px, py, w, h)
            if click:
                self.attempt_select(None, px, py, w, h)

        # Hover/selection by hand pinch
        if pinch_pos is not None:
            px, py = pinch_pos
            self.update_hover_by_position(px, py, w, h)
            if pinch_active:
                self.update_pinch_by_position(px, py, pinch_active, w, h)

    # ==========
    # Drawing
    # ==========

    def draw_grid(self, frame):
        overlay = frame.copy()
        h, w = frame.shape[:2]

        for r in range(self.rows):
            for c in range(self.cols):
                x, y, cw, ch = self.get_cell_rect(r, c, w, h)

                color = CELL_COLOR
                alpha = CELL_ALPHA

                if self.selected[r][c]:
                    color = SELECTED_COLOR
                    alpha = SELECTED_ALPHA
                elif self.hovered[r][c]:
                    color = HOVER_COLOR
                    alpha = HOVER_ALPHA

                cv2.rectangle(overlay, (x, y), (x + cw, y + ch), color, -1)
                cv2.rectangle(overlay, (x, y), (x + cw, y + ch), (255, 255, 255), 1)

        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    def draw_labels(self, frame):
        h, w = frame.shape[:2]
        for r in range(self.rows):
            for c in range(self.cols):
                x, y, cw, ch = self.get_cell_rect(r, c, w, h)
                label_x = int(x + cw * LABEL_LEFT_MARGIN_PCT)
                label_y = int(y + ch * (1 - LABEL_BOTTOM_MARGIN_PCT))
                label = f"{r},{c}"
                cv2.putText(
                    frame,
                    label,
                    (label_x, label_y),
                    LABEL_FONT,
                    LABEL_FONT_SCALE,
                    LABEL_COLOR,
                    LABEL_THICKNESS,
                    cv2.LINE_AA,
                )
        return frame
