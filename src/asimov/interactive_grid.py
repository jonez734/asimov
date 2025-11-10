import cv2
import numpy as np
import time

# --- NAMED CONSTANTS ---
DEFAULT_ROWS = 3
DEFAULT_COLS = 3
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_CELL_THICKNESS = 2
DEFAULT_CELL_COLOR = (0, 255, 0)       # Green fill for active cells
DEFAULT_BORDER_COLOR = (255, 255, 255) # White border
DEFAULT_ALPHA = 0.7                     # Max transparency
DEFAULT_FADE_DURATION = 2.0             # Seconds for fade-in
DEFAULT_TOP_MARGIN_PCT = 0.1
DEFAULT_BOTTOM_MARGIN_PCT = 0.1
DEFAULT_LEFT_MARGIN_PCT = 0.1
DEFAULT_RIGHT_MARGIN_PCT = 0.1

class InteractiveGrid:
    def __init__(self, rows=DEFAULT_ROWS, cols=DEFAULT_COLS,
                 width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT,
                 cell_thickness=DEFAULT_CELL_THICKNESS,
                 cell_color=DEFAULT_CELL_COLOR,
                 border_color=DEFAULT_BORDER_COLOR,
                 alpha=DEFAULT_ALPHA,
                 fade_duration=DEFAULT_FADE_DURATION,
                 top_margin_pct=DEFAULT_TOP_MARGIN_PCT,
                 bottom_margin_pct=DEFAULT_BOTTOM_MARGIN_PCT,
                 left_margin_pct=DEFAULT_LEFT_MARGIN_PCT,
                 right_margin_pct=DEFAULT_RIGHT_MARGIN_PCT):
        self.rows = rows
        self.cols = cols
        self.width = width
        self.height = height
        self.cell_thickness = cell_thickness
        self.cell_color = cell_color
        self.border_color = border_color
        self.alpha = alpha
        self.fade_duration = fade_duration
        self.top_margin_pct = top_margin_pct
        self.bottom_margin_pct = bottom_margin_pct
        self.left_margin_pct = left_margin_pct
        self.right_margin_pct = right_margin_pct

        # Compute effective width and height excluding margins
        self.effective_width = int(self.width * (1.0 - self.left_margin_pct - self.right_margin_pct))
        self.effective_height = int(self.height * (1.0 - self.top_margin_pct - self.bottom_margin_pct))
        self.top_margin = int(self.height * self.top_margin_pct)
        self.bottom_margin = int(self.height * self.bottom_margin_pct)
        self.left_margin = int(self.width * self.left_margin_pct)
        self.right_margin = int(self.width * self.right_margin_pct)

        # Calculate cell size
        self.cell_width = self.effective_width // self.cols
        self.cell_height = self.effective_height // self.rows

        # Grid state
        self.grid_state = np.zeros((self.rows, self.cols), dtype=bool)

        # Fade-in tracking
        self._fade_start_time = None
        self._current_alpha = 0.0

        # Hover tracking
        self.hover_cell = None  # (row, col) currently hovered

    # -----------------------
    # DEVICE-AGNOSTIC INTERACTIONS
    # -----------------------
    def update_hover_by_position(self, x, y):
        """Device-agnostic hover update using coordinates."""
        col = (x - self.left_margin) // self.cell_width
        row = (y - self.top_margin) // self.cell_height
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.hover_cell = (row, col)
        else:
            self.hover_cell = None

    def handle_click_at_position(self, x, y):
        """Device-agnostic click/toggle at coordinates."""
        col = (x - self.left_margin) // self.cell_width
        row = (y - self.top_margin) // self.cell_height
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid_state[row, col] = not self.grid_state[row, col]

    def handle_mouse_event(self, event, x, y, flags, param):
        """Legacy mouse callback for convenience."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.handle_click_at_position(x, y)
        self.update_hover_by_position(x, y)

    # -----------------------
    # DRAWING
    # -----------------------
    def draw_grid(self, frame):
        """Draw the grid with fade-in and hover effect."""
        if self._fade_start_time is None:
            self._fade_start_time = time.time()

        elapsed = time.time() - self._fade_start_time
        fade_ratio = min(elapsed / self.fade_duration, 1.0)
        self._current_alpha = fade_ratio * self.alpha

        overlay = frame.copy()
        for r in range(self.rows):
            for c in range(self.cols):
                top_left = (self.left_margin + c * self.cell_width,
                            self.top_margin + r * self.cell_height)
                bottom_right = (self.left_margin + (c + 1) * self.cell_width,
                                self.top_margin + (r + 1) * self.cell_height)

                # Fill active cells
                if self.grid_state[r, c]:
                    cv2.rectangle(overlay, top_left, bottom_right, self.cell_color, -1)

                # Hover effect
                if self.hover_cell == (r, c):
                    HOVER_COLOR = (0, 255, 255)  # yellow
                    HOVER_ALPHA = 0.3
                    temp_overlay = overlay.copy()
                    cv2.rectangle(temp_overlay, top_left, bottom_right, HOVER_COLOR, -1)
                    cv2.addWeighted(temp_overlay, HOVER_ALPHA, overlay, 1 - HOVER_ALPHA, 0, overlay)

                # Draw border
                cv2.rectangle(overlay, top_left, bottom_right, self.border_color, self.cell_thickness)

        # Blend overlay
        cv2.addWeighted(overlay, self._current_alpha, frame, 1 - self._current_alpha, 0, frame)

    # -----------------------
    # GRID RESET
    # -----------------------
    def reset_grid(self):
        """Reset all cells and restart fade-in."""
        self.grid_state[:] = False
        self._fade_start_time = None
        self._current_alpha = 0.0
        self.hover_cell = None
