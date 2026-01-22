# asimov/modules/float_playingcard.py
#
# Floating playing card module
# Emits RGBA layer only (no frame mutation)
#

import cv2
import numpy as np

from asimov import conf

# ------------------------------------------------------------
# Module state (private)
# ------------------------------------------------------------

_card_cache = {}     # path -> RGBA image
_last_path = None
_card_image = None

# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _load_card():
    """
    Load card image based on *current runtime config*.
    Reloads automatically if the path changes.
    """
    global _card_image, _last_path

    path = conf.FLOAT_PLAYINGCARD.get("IMAGE")
    if not path:
        raise RuntimeError("FLOAT_PLAYINGCARD.IMAGE not set")

    # Fast path: same card as last frame
    if path == _last_path:
        return

    # Cached path
    if path in _card_cache:
        _card_image = _card_cache[path]
        _last_path = path
        return

    # Load from disk
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"Failed to load card image: {path}")

    # Ensure RGBA
    if img.shape[2] == 3:
        alpha = np.full(img.shape[:2], 255, dtype=np.uint8)
        img = np.dstack((img, alpha))

    _card_cache[path] = img
    _card_image = img
    _last_path = path


def _render_rgba(dst, src, x, y):
    """
    Alpha-blit src RGBA into dst RGBA at (x, y).
    """
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

    alpha = src_roi[..., 3:4] / 255.0
    dst_roi[..., :3][:] = (
        (1.0 - alpha) * dst_roi[..., :3] +
        alpha * src_roi[..., :3]
    )
    dst_roi[..., 3] = np.maximum(dst_roi[..., 3], src_roi[..., 3])

# ------------------------------------------------------------
# Module ABI
# ------------------------------------------------------------

def detect(frame, context, /, **kw):
    """
    Compute card placement.
    Writes geometry only.
    """
    _load_card()

    hand = getattr(context, "primary_hand", None)
    if hand is None:
        context.card = None
        return

    cx, cy = hand["center"]

    context.card = {
        "center": (int(cx), int(cy)),
        "scale": conf.FLOAT_PLAYINGCARD.get("SCALE", 1.0),
        "angle": conf.FLOAT_PLAYINGCARD.get("ROTATION", 0),
    }


def draw(frame, context, /, **kw):
    """
    Render card into RGBA layer.
    Frame is returned unchanged.
    """
    card = getattr(context, "card", None)
    if card is None:
        context.layers.pop("card", None)
        return frame

    h, w = frame.shape[:2]
    layer = np.zeros((h, w, 4), dtype=np.uint8)

    img = _card_image

    # Scale
    if card["scale"] != 1.0:
        img = cv2.resize(
            img,
            None,
            fx=card["scale"],
            fy=card["scale"],
            interpolation=cv2.INTER_LINEAR,
        )

    # Rotate
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

    x = card["center"][0] - img.shape[1] // 2
    y = card["center"][1] - img.shape[0] // 2

    _render_rgba(layer, img, x, y)

    context.layers["card"] = layer
    return frame
