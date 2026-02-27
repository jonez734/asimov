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
from asimov.common import OneEuroFilter
from asimov.playingcard import cards
from . import glitch

RANKS = cards.RANKS
SUITS = cards.SUITS

# ------------------------------------------------------------
# Module state (private)
# ------------------------------------------------------------

_card_cache = {}  # path -> RGBA image
_last_path = None
_card_image = None

_current_rank = None
_current_suit = None

_start_time = time.monotonic()

_basedir = None
_set_name = None

_last_hand_detected_time = None
_SHOW_DELAY = 0.1  # 100ms to show card after hand detected
_HIDE_DELAY = 0.3  # 300ms to hide card after hand lost

# OneEuroFilter for stabilization
_filter_x = None
_filter_y = None
_filter_scale = None
_current_phase = None

# Filter params (tune these)
_FILTER_FREQ = 30
_FILTER_MIN_CUTOFF = 0.4  # lower = smoother
_FILTER_BETA = 0.005  # lower = less responsive to speed

# Hand detection
_MIN_CONFIDENCE = 0.5  # set to 0 to disable

# ------------------------------------------------------------
# UI Schema (Dashboard Integration)
# ------------------------------------------------------------


def ui_schema(args=None, context=None):
    return {
        "Card": {
            "rank": {"type": "enum", "enum": RANKS, "label": "Rank"},
            "suit": {"type": "enum", "enum": SUITS, "label": "Suit"},
            "opacity": {
                "type": "float",
                "default": 0.8,
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "label": "Opacity",
            },
            "glitch": {"type": "bool", "default": True, "label": "Enable Glitch"},
        },
    }


# ------------------------------------------------------------
# Lifecycle Hooks
# ------------------------------------------------------------


def init(args, context=None, **kwargs):
    global _basedir, _set_name

    _basedir = os.path.expandvars(
        os.path.expanduser(
            getattr(
                args,
                "basedir",
                conf.PLAYINGCARD.get("BASEDIR", "$HOME/projects/playingcarddata"),
            )
        )
    )
    _set_name = getattr(args, "set_name", conf.PLAYINGCARD.get("SET_NAME", "bicycle"))

    glitch.set_max_concurrent(2)
    glitch.register("scanlines")
    glitch.register("ghost", alpha=0.3, shift=8)
    glitch.register("whitenoise", amount=0.1)
    glitch.register("tearing")

    return True


# ------------------------------------------------------------
# Detection
# ------------------------------------------------------------


def _run_glitch_detection(frame, context):
    """Run glitch scheduler to trigger random glitches."""
    try:
        glitch.detect(frame, context)
    except Exception:
        pass


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

    src_roi = src[sy0 : sy0 + (y1 - y0), sx0 : sx0 + (x1 - x0)]
    dst_roi = dst[y0:y1, x0:x1]

    alpha = (src_roi[..., 3:4] / 255.0) * opacity
    dst_roi[..., :3][:] = (1.0 - alpha) * dst_roi[..., :3] + alpha * src_roi[..., :3]
    dst_roi[..., 3] = np.maximum(dst_roi[..., 3], src_roi[..., 3])


def _stable_phase(seed) -> float:
    h = hashlib.sha1(str(seed).encode("utf-8")).digest()
    v = int.from_bytes(h[:4], "little")
    return (v / 2**32) * (2 * math.pi)


def _float_offset(phase):
    t = time.monotonic() - _start_time

    amplitude = conf.FLOAT_PLAYINGCARD.get("FLOAT_AMPLITUDE", 12)
    frequency = conf.FLOAT_PLAYINGCARD.get("FLOAT_FREQUENCY", 0.5)

    return int(math.sin(2 * math.pi * frequency * t + phase) * amplitude)


def _get_hand_center(context):
    hand = getattr(context, "primary_hand", None)
    if hand is not None:
        return hand.get("center")

    hand_ns = context.get("HAND")
    if hand_ns:
        hands = hand_ns.get("hands") or []
        if hands:
            first_hand = hands[0]
            bbox = first_hand.get("bbox")
            if bbox:
                cx = bbox[0] + bbox[2] // 2
                cy = bbox[1] + bbox[3] // 2
                return (cx, cy), bbox, first_hand

    return None, None, None


def _is_hand_open(hand):
    if not hand:
        return False

    lm = hand.get("lmList")
    if not lm or len(lm) < 21:
        return False

    def finger_extended(tip_idx, mcp_idx):
        tip = lm[tip_idx]
        mcp = lm[mcp_idx]
        dist = ((tip[0] - mcp[0]) ** 2 + (tip[1] - mcp[1]) ** 2) ** 0.5
        return dist > 30

    fingers = [
        finger_extended(8, 5),  # index
        finger_extended(12, 9),  # middle
        finger_extended(16, 13),  # ring
        finger_extended(20, 17),  # pinky
    ]

    return sum(fingers) >= 3


# ------------------------------------------------------------
# Module ABI
# ------------------------------------------------------------


def detect(frame, context, /, **kw):
    global _last_hand_detected_time, _filter_x, _filter_y, _filter_scale, _current_phase

    _run_glitch_detection(frame, context)

    center, bbox, hand = _get_hand_center(context)

    hand_detected = center is not None and _is_hand_open(hand)
    # Optional confidence check - set _MIN_CONFIDENCE to 0 to disable
    if _MIN_CONFIDENCE > 0:
        conf_val = hand.get("confidence") if hand else None
        if conf_val is not None and conf_val < _MIN_CONFIDENCE:
            hand_detected = False
    now = time.monotonic()

    if hand_detected:
        _last_hand_detected_time = now

        cx, cy = center

        hand_width = bbox[2] if bbox else 100
        card_width = _card_image.shape[1] if _card_image is not None else 100
        target_scale = (hand_width / card_width) * conf.FLOAT_PLAYINGCARD.get(
            "SCALE", 0.8
        )

        if _filter_x is None:
            _filter_x = OneEuroFilter(
                freq=_FILTER_FREQ,
                min_cutoff=_FILTER_MIN_CUTOFF,
                beta=_FILTER_BETA,
                init=cx,
            )
            _filter_y = OneEuroFilter(
                freq=_FILTER_FREQ,
                min_cutoff=_FILTER_MIN_CUTOFF,
                beta=_FILTER_BETA,
                init=cy,
            )
            _filter_scale = OneEuroFilter(
                freq=_FILTER_FREQ,
                min_cutoff=_FILTER_MIN_CUTOFF,
                beta=_FILTER_BETA,
                init=target_scale,
            )
            _current_phase = _stable_phase((int(cx), int(cy)))
            smoothed_cx, smoothed_cy, smoothed_scale = cx, cy, target_scale
        else:
            smoothed_cx = _filter_x.update(cx)
            smoothed_cy = _filter_y.update(cy)
            smoothed_scale = _filter_scale.update(target_scale)

        context.card = {
            "center": (int(smoothed_cx), int(smoothed_cy)),
            "scale": smoothed_scale,
            "angle": conf.FLOAT_PLAYINGCARD.get("ROTATION", 0),
            "phase": _current_phase,
        }
    else:
        if _last_hand_detected_time is not None:
            if now - _last_hand_detected_time < _HIDE_DELAY:
                return

        _last_hand_detected_time = None
        _filter_x = None
        _filter_y = None
        _filter_scale = None
        _current_phase = None
        context.card = None


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

    enable_glitch = card_config.get(
        "glitch", conf.FLOAT_PLAYINGCARD.get("GLITCH", True)
    )
    if config:
        enable_glitch = config.get("glitch", enable_glitch)

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

    if enable_glitch:
        try:
            img = glitch.draw(img, context)
        except Exception:
            pass

    _render_rgba(layer, img, x, y, opacity)

    if layer.shape[2] == 4:
        card_alpha = layer[..., 3:4] / 255.0
        card_rgb = layer[..., :3]
        frame[..., :3] = (
            card_rgb * card_alpha + frame[..., :3] * (1.0 - card_alpha)
        ).astype(np.uint8)

    return frame
