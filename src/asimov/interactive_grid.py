# asimov/interactive_grid.py
import cv2

# ----------------------------
# Constants
# ----------------------------
COLOR_CELL = (50, 50, 200)
COLOR_CELL_HOVER = (80, 80, 255)
COLOR_CELL_SELECTED = (0, 200, 0)
COLOR_TIP = (0, 255, 255)
COLOR_CONFIRM = (0, 255, 0)
COLOR_CONFIRM_HOVER = (0, 200, 0)
RADIUS_TIP = 8
MARGIN_RATIO = 0.1
ALPHA_GRID = 0.7
SCALE_HOVER = 1.1

class InteractiveGrid:
    def __init__(self, rects):
        """
        rects: list of rectangles [(x1,y1,x2,y2), ...]
        """
        self.rects = rects
        self.active_index = None
        self.selected_index = None
        self.hands = []

    # ----------------------------
    # Update hands (robust)
    # ----------------------------
    def update_hands(self, hands):
        """
        hands: list of hands detected by cvzone/mediapipe
        Accepts list of dicts or list of landmark lists
        """
        self.hands = hands or []

    # ----------------------------
    # Hover detection (robust)
    # ----------------------------
    def update_hover(self):
        """
        Updates self.active_index based on index fingertip position
        """
        self.active_index = None
        if not self.hands:
            return

        hand = self.hands[0]

        # Support dict or list
        if isinstance(hand, dict):
            lmList = hand.get("lmList", [])
        elif isinstance(hand, list):
            lmList = hand
        else:
            return

        if len(lmList) <= 8 or len(lmList[8]) < 2:
            return

        cx, cy = lmList[8][:2]

        for i, rect in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            margin_x = int((x2 - x1) * MARGIN_RATIO)
            margin_y = int((y2 - y1) * MARGIN_RATIO)
            if x1 + margin_x <= cx <= x2 - margin_x and y1 + margin_y <= cy <= y2 - margin_y:
                self.active_index = i
                break

    # ----------------------------
    # Draw yellow tip circles
    # ----------------------------
    def draw_tips(self, frame):
        """
        Draws yellow circles at thumb (4) and index (8) tips
        """
        if not self.hands:
            return

        hand = self.hands[0]

        if isinstance(hand, dict):
            lmList = hand.get("lmList", [])
        elif isinstance(hand, list):
            lmList = hand
        else:
            return

        for tip_index in [4, 8]:  # thumb tip and index tip
            if len(lmList) > tip_index and len(lmList[tip_index]) >= 2:
                x, y = lmList[tip_index][:2]
                cv2.circle(frame, (int(x), int(y)), RADIUS_TIP, COLOR_TIP, -1)

    # ----------------------------
    # Draw the grid (cells only)
    # ----------------------------
    def draw_grid(self, frame):
        """
        Draws grid rectangles with hover and selection coloring
        """
        overlay = frame.copy()
        for i, rect in enumerate(self.rects):
            x1, y1, x2, y2 = rect
            color = COLOR_CELL
            if i == self.selected_index:
                color = COLOR_CELL_SELECTED
            elif i == self.active_index:
                color = COLOR_CELL_HOVER

            # Draw rectangle
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)

        # Apply alpha blending
        cv2.addWeighted(overlay, ALPHA_GRID, frame, 1 - ALPHA_GRID, 0, frame)

    # ----------------------------
    # Select active cell
    # ----------------------------
    def select_active(self):
        if self.active_index is not None:
            self.selected_index = self.active_index

    # ----------------------------
    # Reset selection
    # ----------------------------
    def reset_selection(self):
        self.selected_index = None
