# asimov/modules/float_playingcard.py
#
# Floating playing card module
# Consolidated from float_card.py and float_playingcard.py
# Features:
# - Dashboard-based rank/suit selection
# - Config-based single image mode
# - Floating animation with per-card phase offset
# - Glitch effects support

import os
import cv2
import numpy as np
import time
import math
import hashlib

from asimov import conf
from asimov.common import ThreadSafeContext
from asimov.playingcard import cards
from asimov.modules import glitch

RANKS = cards.RANKS
SUITS = cards.SUITS

# ------------------------------------------------------------
# Module state (private)
# ------------------------------------------------------------

_card_cache = {}     # path -> RGBA image
_last_path = None
_card_image = None

_current_rank = None
_current_suit = None

_start_time = time.monotonic()

_basedir = None
_set_name = None

# ------------------------------------------------------------
# UI Schema (Dashboard Integration)
# ------------------------------------------------------------

def ui_schema(args=None, context=None):
    return {
        "Card": {
            "rank": {
                "type": "enum",
                "enum": RANKS,
                "label": "Rank"
            },
            "suit": {
                "type": "enum",
                "enum": SUITS,
                "label": "Suit"
            },
            "opacity": {
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "label": "Opacity"
            },
        },
    }


# ------------------------------------------------------------
# Lifecycle Hooks
# ------------------------------------------------------------

def init(args, context=None, **kwargs):
    global _basedir, _set_name

    _basedir = os.path.expandvars(os.path.expanduser(
        getattr(args, "basedir", conf.PLAYINGCARD.get("BASEDIR", "$HOME/projects/playingcarddata"))
    ))
    _set_name = getattr(args, "set_name", conf.PLAYINGCARD.get("SET_NAME", "bicycle"))

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
# Internal helpers
# ------------------------------------------------------------

def _load_card_from_assets(rank, suit):
    return cards.load_card_image(rank, suit, _basedir, _set_name)


def _load_card_from_config():
    global _card_image, _last_path

    path = conf.FLOAT_PLAYINGCARD.get("IMAGE")
    if not path:
        img = cards.load_card_image("queen", "spades", _basedir, _set_name)
        if img is not None:
            _card_image = img
            _last_path = "default"
        return img

    if path == _last_path and _card_image is not None:
        return _card_image

    if path in _card_cache:
        _card_image = _card_cache[path]
        _last_path = path
        return _card_image

    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None

    if img.shape[2] == 3:
        alpha = np.full(img.shape[:2], 255, dtype=np.uint8)
        img = np.dstack((img, alpha))

    _card_cache[path] = img
    _card_image = img
    _last_path = path
    return _card_image


def _render_rgba(dst, src, x, y, opacity=1.0):
    h, w = src.shape[:2]
    H, W = dst.shape[:2]

    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)

    if x1 <= x0 or y1 <= y0:
        return

    sx0 = x0 - x
    sy0 = y0 - y

    src_roi = src[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
    dst_roi = dst[y0:y1, x0:x1]

    alpha = (src_roi[..., 3:4] / 255.0) * opacity
    dst_roi[..., :3][:] = (
        (1.0 - alpha) * dst_roi[..., :3] +
        alpha * src_roi[..., :3]
    )
    dst_roi[..., 3] = np.maximum(dst_roi[..., 3], src_roi[..., 3])


def _stable_phase(seed) -> float:
    h = hashlib.sha1(str(seed).encode("utf-8")).digest()
    v = int.from_bytes(h[:4], "little")
    return (v / 2**32) * (2 * math.pi)


def _float_offset(phase):
    t = time.monotonic() - _start_time

    amplitude = conf.FLOAT_PLAYINGCARD.get("FLOAT_AMPLITUDE", 12)
    frequency = conf.FLOAT_PLAYINGCARD.get("FLOAT_FREQUENCY", 0.5)

    return int(
        math.sin(2 * math.pi * frequency * t + phase) * amplitude
    )


def _get_hand_center(context):
    hand = getattr(context, "primary_hand", None)
    if hand is not None:
        return hand.get("center")

    hand_ns = context.get("HAND")
    if hand_ns:
        bbox = hand_ns.get("bbox")
        if bbox:
            cx = bbox[0] + bbox[2] // 2
            cy = bbox[1] + bbox[3] // 2
            return (cx, cy)

    return None


# ------------------------------------------------------------
# Module ABI
# ------------------------------------------------------------

def detect(frame, context, /, **kw):
    center = _get_hand_center(context)
    if center is None:
        context.card = None
        return

    cx, cy = center
    seed = (int(cx), int(cy))

    context.card = {
        "center": (int(cx), int(cy)),
        "scale": conf.FLOAT_PLAYINGCARD.get("SCALE", 1.0),
        "angle": conf.FLOAT_PLAYINGCARD.get("ROTATION", 0),
        "phase": _stable_phase(seed),
    }


def draw(frame, context, /, config=None, **kw):
    global _card_image, _current_rank, _current_suit

    card_config = conf.FLOAT_PLAYINGCARD.get("Card", {})

    rank = card_config.get("rank")
    suit = card_config.get("suit")
    opacity = card_config.get("opacity", conf.FLOAT_PLAYINGCARD.get("OPACITY", 0.8))

    if config:
        rank = config.get("rank", rank)
        suit = config.get("suit", suit)
        opacity = config.get("opacity", opacity)

    if rank and suit:
        if rank != _current_rank or suit != _current_suit:
            _card_image = _load_card_from_assets(rank, suit)
            _current_rank = rank
            _current_suit = suit
    else:
        _load_card_from_config()

    if _card_image is None:
        return frame

    card = getattr(context, "card", None)
    if card is None:
        return frame

    h, w = frame.shape[:2]
    layer = np.zeros((h, w, 4), dtype=np.uint8)

    img = _card_image.copy()

    if card["scale"] != 1.0:
        img = cv2.resize(
            img,
            None,
            fx=card["scale"],
            fy=card["scale"],
            interpolation=cv2.INTER_LINEAR,
        )

    if card["angle"]:
        ih, iw = img.shape[:2]
        M = cv2.getRotationMatrix2D((iw / 2, ih / 2), card["angle"], 1.0)
        img = cv2.warpAffine(
            img,
            M,
            (iw, ih),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )

    dy = _float_offset(card["phase"])

    x = card["center"][0] - img.shape[1] // 2
    y = card["center"][1] - img.shape[0] // 2 + dy

    glitch.scheduler()
    if glitch.is_any_glitch_running():
        img = glitch.apply(img)

    _render_rgba(layer, img, x, y, opacity)

    context.layers["card"] = layer
    return frame
