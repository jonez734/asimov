import cv2
import numpy as np
import time
from math import sin, pi

class InteractiveGrid:
    def __init__(self, items, cols, rows, hover_pulse_freq=2.0,
                 margin_ratio=0.05, hover_scale=1.1, flash_duration=0.3):
        """
        items: list of strings (labels)
        cols, rows: grid layout
        hover_pulse_freq: pulse frequency in Hz
        margin_ratio: fraction of cell width/height used for hover detection margin
        hover_scale: scale multiplier for hovered cell
        flash_duration: seconds for selection flash
        """
        assert len(items) > 0 and cols > 0 and rows > 0, "Invalid grid dimensions"

        self.items = items
        self.cols = cols
        self.rows = rows
        self.hover_pulse_freq = hover_pulse_freq
        self.margin_ratio = margin_ratio
        self.hover_scale = hover_scale
        self.flash_duration = flash_duration

        # Active state
        self.active_index = None
        self.alpha_overlay = 1.0
        self.scale = 0.0  # start shrunk
        self.last_time = time.time()

        # Layout
        self.rects = []
        self.cell_w = 0
        self.cell_h = 0

        # Selection flash tracking
        self.selection_flash = {}  # index -> timestamp

    # ----------------------------
    # Layout helpers
    # ----------------------------
    def compute_rects(self, frame_w, frame_h):
        # Occupy ~80% width, ~50% height
        max_grid_w = int(frame_w * 0.8)
        max_grid_h = int(frame_h * 0.5)
        self.cell_w = int(max_grid_w / self.cols)
        self.cell_h = int(max_grid_h / self.rows)

        # Center the grid
        total_w = self.cell_w * self.cols
        total_h = self.cell_h * self.rows
        start_x = (frame_w - total_w) // 2
        start_y = (frame_h - total_h) // 2

        self.rects = []
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                if idx >= len(self.items):
                    break
                x1 = start_x + c * self.cell_w
                y1 = start_y + r * self.cell_h
                x2 = x1 + self.cell_w
                y2 = y1 + self.cell_h
                self.rects.append((x1, y1, x2, y2))

    def get_cell_rect(self, index):
        if index < 0 or index >= len(self.rects):
            return None
        return self.rects[index]

    def get_cell_center(self, index):
        rect = self.get_cell_rect(index)
        if rect is None:
            return None
        x1, y1, x2, y2 = rect
        return (x1 + x2)//2, (y1 + y2)//2

    # ----------------------------
    # Hover detection
    # ----------------------------
    def update_hover(self, hands):
        self.active_index = None
        if not hands:
            return
        lmList = hands[0].get("lmList", [])
        if len(lmList) <= 8 or len(lmList[8]) < 2:
            return
        cx, cy = lmList[8][:2]  # index fingertip

        for i, rect in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            margin_x = int(self.cell_w * self.margin_ratio)
            margin_y = int(self.cell_h * self.margin_ratio)
            if x1 + margin_x <= cx <= x2 - margin_x and y1 + margin_y <= cy <= y2 - margin_y:
                self.active_index = i
                break

    # ----------------------------
    # Time-based animation
    # ----------------------------
    def animate_in(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        scale_speed = 2.0  # units/sec
        alpha_speed = 2.0

        self.scale = min(1.0, self.scale + dt * scale_speed)
        self.alpha_overlay = min(1.0, self.alpha_overlay + dt * alpha_speed)

    # ----------------------------
    # Drawing helpers
    # ----------------------------
    def apply_hover_overlay(self, frame, rect, color, alpha):
        x1, y1, x2, y2 = rect
        overlay = frame[y1:y2, x1:x2].copy()
        color_layer = np.full((y2 - y1, x2 - x1, 3), color, dtype=np.uint8)
        blended = cv2.addWeighted(overlay, 1 - alpha, color_layer, alpha, 0)
        frame[y1:y2, x1:x2] = blended

    def draw_label_centered(self, frame, rect, text, font_scale=1.0, thickness=2):
        x1, y1, x2, y2 = rect
        cx, cy = (x1 + x2)//2, (y1 + y2)//2
        size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        cv2.putText(frame, text, (cx - size[0]//2, cy + size[1]//2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255,255,255), thickness, cv2.LINE_AA)

    # ----------------------------
    # Register a selection for visual feedback
    # ----------------------------
    def record_selection(self, index):
        if 0 <= index < len(self.rects):
            self.selection_flash[index] = time.time()

    # ----------------------------
    # Draw grid
    # ----------------------------
    def draw(self, frame, hands=None):
        if not self.rects:
            self.compute_rects(frame.shape[1], frame.shape[0])

        self.update_hover(hands)
        self.animate_in()

        t = time.time()
        for i, rect in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            color = (0, 128, 255)  # base rectangle color

            # ------------------------
            # Handle hover pulse & scaling
            # ------------------------
            scale = self.scale
            if i == self.active_index:
                pulse = 0.2 * sin(2 * pi * self.hover_pulse_freq * t)
                scale *= self.hover_scale
            else:
                pulse = 0.0

            # Compute scaled rect
            cx, cy = (x1 + x2)//2, (y1 + y2)//2
            w, h = int((x2 - x1) * scale), int((y2 - y1) * scale)
            x1s, y1s = cx - w//2, cy - h//2
            x2s, y2s = cx + w//2, cy + h//2
            scaled_rect = (x1s, y1s, x2s, y2s)

            # Hover overlay
            if i == self.active_index:
                self.apply_hover_overlay(frame, scaled_rect, color, alpha=0.3 + pulse)

            # Selection flash overlay
            if i in self.selection_flash:
                elapsed = t - self.selection_flash[i]
                if elapsed < self.flash_duration:
                    alpha_flash = 0.5 * (1.0 - elapsed/self.flash_duration)
                    self.apply_hover_overlay(frame, scaled_rect, (0,255,0), alpha_flash)
                else:
                    del self.selection_flash[i]

            # Draw outline
            cv2.rectangle(frame, (x1s, y1s), (x2s, y2s), color, 3)
            # Draw label
            self.draw_label_centered(frame, scaled_rect, self.items[i])
