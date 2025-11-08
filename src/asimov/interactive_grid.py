import cv2
import numpy as np
from math import sin, pi
import time

class InteractiveGrid:
    """
    Interactive grid for hand-controlled selection.
    Supports hover highlighting, pinch detection, and alpha blending transitions.
    """

    def __init__(self, items, cols, rows, hover_pulse_freq=2.0):
        self.items = items
        self.cols = cols
        self.rows = rows
        self.hover_pulse_freq = hover_pulse_freq

        # Active state
        self.active_index = None
        self.alpha_overlay = 1.0

        # Layout
        self.rects = []
        self.cell_w = 0
        self.cell_h = 0

        # Animation
        self.scale = 1.0

    # ----------------------------
    # Layout and drawing helpers
    # ----------------------------

    def compute_rects(self, frame_w, frame_h):
        """Compute rectangle positions to center the grid."""
        self.cell_w = frame_w // (self.cols + 2)
        self.cell_h = frame_h // (self.rows + 4)

        grid_w = self.cell_w * self.cols
        grid_h = self.cell_h * self.rows
        start_x = (frame_w - grid_w) // 2
        start_y = (frame_h - grid_h) // 2

        self.rects = []
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = start_x + c * self.cell_w
                y1 = start_y + r * self.cell_h
                x2 = x1 + self.cell_w
                y2 = y1 + self.cell_h
                self.rects.append((x1, y1, x2, y2))

    def draw(self, frame, hands=None):
        """
        Draw grid onto the frame.
        hands: optional CvZone hands list for hover detection
        """
        if not self.rects:
            self.compute_rects(frame.shape[1], frame.shape[0])

        # Update hover
        self.update_hover(hands)

        overlay = frame.copy()
        t = time.time()
        pulse = 0
        if self.active_index is not None:
            pulse = 0.2 * sin(2 * pi * self.hover_pulse_freq * t)

        for i, rect in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            color = (0, 200, 255) if i == self.active_index else (255, 255, 255)
            thickness = 3

            # Draw rectangle
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)

            # Draw label
            if i < len(self.items):
                label = str(self.items[i])
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 1.5
                (w, h), _ = cv2.getTextSize(label, font, scale, thickness)
                tx = x1 + (self.cell_w - w) // 2
                ty = y1 + (self.cell_h + h) // 2
                cv2.putText(overlay, label, (tx, ty), font, scale, (255, 255, 255), thickness)

        blend_alpha = min(1.0, self.alpha_overlay + pulse)
        cv2.addWeighted(overlay, blend_alpha, frame, 1 - blend_alpha, 0, frame)

    # ----------------------------
    # Interaction helpers
    # ----------------------------

    def update_hover(self, hands):
        """Update active_index based on first hand index finger."""
        self.active_index = None
        if not hands:
            return
        lmList = hands[0]["lmList"]
        cx, cy = lmList[8][:2]  # index fingertip
        for i, (x1, y1, x2, y2) in enumerate(self.rects):
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                self.active_index = i
                break

    def get_active_item(self):
        """Return the currently active item (label) or None."""
        if self.active_index is None or self.active_index >= len(self.items):
            return None
        return self.items[self.active_index]

    # ----------------------------
    # Animation helpers
    # ----------------------------

    def animate_in(self, scale_step=0.02, alpha_step=0.03):
        """Simple time-based animation step. Returns True if animation ongoing."""
        updated = False
        if self.scale < 1.0:
            self.scale += scale_step
            if self.scale > 1.0:
                self.scale = 1.0
            updated = True
        if self.alpha_overlay < 1.0:
            self.alpha_overlay += alpha_step
            if self.alpha_overlay > 1.0:
                self.alpha_overlay = 1.0
            updated = True
        return updated
