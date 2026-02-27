# UNUSED - DEPRECATED
# This module is not used by main_dashboard. Use float_playingcard.py instead.
# Left for reference only.

# asimov/overlays/float_card.py

import os
import cv2
import numpy as np

from asimov.common import ThreadSafeContext
from asimov.util import safe_path
from asimov import glitch


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["hearts", "diamonds", "clubs", "spades"]

PALM_SCALE_FACTOR = 1.5

_card_img = None
_current_rank = None
_current_suit = None
_opacity = 0.8


# ------------------------------------------------------------
# UI Schema (Dashboard Integration)
# ------------------------------------------------------------

def ui_schema():
    return {
        "title": "Floating Playing Card",
        "type": "object",
        "properties": {
            "rank": {
                "type": "string",
                "title": "Rank",
                "enum": RANKS,
            },
            "suit": {
                "type": "string",
                "title": "Suit",
                "enum": SUITS,
            },
            "opacity": {
                "type": "number",
                "title": "Opacity",
                "minimum": 0.1,
                "maximum": 1.0,
                "default": 0.8,
            },
        },
    }


# ------------------------------------------------------------
# Lifecycle Hooks
# ------------------------------------------------------------

def init(args, context=None, **kwargs):
    """
    Setup glitch framework once.
    No card loading here (runtime-configurable).
    """
    glitch.set_max_concurrent(2)
    glitch.register("scanlines")
    glitch.register("vhs_warp", intensity=7, frequency=3.0, speed=1.5)
    glitch.register("ghost", alpha=0.3, shift=8)
    return True


def access(args, op, /, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def main(args, **kwargs):
    return True


# ------------------------------------------------------------
# Internal Helpers
# ------------------------------------------------------------

def _load_card(rank, suit):
    filename = f"{rank}_of_{suit}.png"
    card_path = safe_path(os.path.join("assets/cards", filename))
    return cv2.imread(card_path, cv2.IMREAD_UNCHANGED)


def _overlay_image_on_frame(frame, card_img, bbox, opacity):
    hand_w = bbox[2]
    target_w = int(hand_w * PALM_SCALE_FACTOR)

    original_h, original_w, _ = card_img.shape
    target_h = int((target_w / original_w) * original_h)

    if target_w < 10 or target_h < 10:
        return frame

    resized_card = cv2.resize(
        card_img,
        (target_w, target_h),
        interpolation=cv2.INTER_AREA
    )

    center_x = bbox[0] + hand_w // 2
    center_y = bbox[1] + bbox[3] // 4

    x1 = int(center_x - target_w // 2)
    y1 = int(center_y - target_h // 2)
    x2 = x1 + target_w
    y2 = y1 + target_h

    h_frame, w_frame, _ = frame.shape

    x1_final = max(0, x1)
    y1_final = max(0, y1)
    x2_final = min(w_frame, x2)
    y2_final = min(h_frame, y2)

    card_crop_x1 = x1_final - x1
    card_crop_y1 = y1_final - y1
    card_crop_x2 = target_w - (x2 - x2_final)
    card_crop_y2 = target_h - (y2 - y2_final)

    card_to_overlay = resized_card[
        card_crop_y1:card_crop_y2,
        card_crop_x1:card_crop_x2
    ]

    alpha_channel = (card_to_overlay[:, :, 3] / 255.0) * opacity
    color_channels = card_to_overlay[:, :, :3]

    roi = frame[y1_final:y2_final, x1_final:x2_final]

    for c in range(3):
        roi[:, :, c] = (
            roi[:, :, c] * (1 - alpha_channel)
            + color_channels[:, :, c] * alpha_channel
        )

    frame[y1_final:y2_final, x1_final:x2_final] = roi

    return frame


# ------------------------------------------------------------
# Detect (No detection here; consume HAND module output)
# ------------------------------------------------------------

def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    return


# ------------------------------------------------------------
# Draw (Runtime Config Aware)
# ------------------------------------------------------------

def draw(frame: np.ndarray, context: ThreadSafeContext, config=None, **kwargs) -> np.ndarray:
    global _card_img, _current_rank, _current_suit, _opacity

    if not config:
        return frame

    rank = config.get("rank")
    suit = config.get("suit")

    # If selection cleared → remove card
    if not rank or not suit:
        _card_img = None
        _current_rank = None
        _current_suit = None
        return frame

    # Detect dashboard change
    if rank != _current_rank or suit != _current_suit:
        img = _load_card(rank, suit)
        if img is not None:
            _card_img = img
            _current_rank = rank
            _current_suit = suit

    if _card_img is None:
        return frame

    _opacity = config.get("opacity", 0.8)

    hand_ns = context.get("HAND")
    if not hand_ns:
        return frame

    bbox = hand_ns.get("bbox")
    if not bbox:
        return frame

    glitch.scheduler()

    card_img = _card_img.copy()

    if glitch.is_any_glitch_running():
        card_img = glitch.apply(card_img)

    return _overlay_image_on_frame(frame, card_img, bbox, _opacity)
