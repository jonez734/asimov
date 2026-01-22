# asimov/eyes_next.py

import cv2
import time
import numpy as np

from . import conf
from .common import ThreadSafeContext, OneEuroFilter

# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _draw_rotated_bar(img, center, size, angle_deg, color, alpha):
    """Draw a rotated rectangle with alpha blending."""
    rect = ((center[0], center[1]), (size[0], size[1]), angle_deg)
    box = cv2.boxPoints(rect).astype(int)

    overlay = img.copy()
    cv2.fillConvexPoly(overlay, box, color)
    cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)


def _expire_bar(ns):
    bar = ns.get("data")
    if not bar:
        return

    if time.time() - bar["timestamp"] > conf.EYES["BAR"]["GRACE_PERIOD"]:
        ns["data"] = None


# ------------------------------------------------------------
# Module API
# ------------------------------------------------------------

def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    """
    Eye privacy-bar detection.

    Consumes:
        context["FACE"]["faces"]

    Produces:
        context["EYES"]["data"]
    """

    face_ns = context.get("FACE")
    if not face_ns or not face_ns.get("faces"):
        if "EYES" in context:
            _expire_bar(context["EYES"])
        return

    faces = face_ns["faces"]
    face = faces[0]

    # --------------------------------------------------------
    # Lazy init
    # --------------------------------------------------------
    if "EYES" not in context:
        f = conf.EYES["FILTER"]
        context["EYES"] = {
            "ema": {
                k: OneEuroFilter(
                    freq=f["FREQ"],
                    min_cutoff=f["MIN_CUTOFF"],
                    beta=f["BETA"],
                )
                for k in ("cx", "cy", "w", "h", "angle")
            },
            "data": None,
        }

    ns = context["EYES"]

    # --------------------------------------------------------
    # Landmark extraction
    # --------------------------------------------------------
    lm = conf.EYES["FACEMESH"]["LANDMARKS"]

    left_pts = np.array([face[i] for i in lm["LEFT_EYE"]], dtype=np.float32)
    right_pts = np.array([face[i] for i in lm["RIGHT_EYE"]], dtype=np.float32)

    all_pts = np.vstack((left_pts, right_pts))

    # --------------------------------------------------------
    # Geometry
    # --------------------------------------------------------
    min_xy = np.min(all_pts, axis=0)
    max_xy = np.max(all_pts, axis=0)

    cx = (min_xy[0] + max_xy[0]) * 0.5
    cy = (min_xy[1] + max_xy[1]) * 0.5
    raw_w = max_xy[0] - min_xy[0]
    raw_h = max_xy[1] - min_xy[1]

    left_center = np.mean(left_pts, axis=0)
    right_center = np.mean(right_pts, axis=0)

    delta = right_center - left_center
    angle = np.degrees(np.arctan2(delta[1], delta[0]))

    # --------------------------------------------------------
    # Filtering
    # --------------------------------------------------------
    ema = ns["ema"]

    ns["data"] = {
        "cx": ema["cx"].update(cx),
        "cy": ema["cy"].update(cy),
        "w": ema["w"].update(raw_w * conf.EYES["BAR"]["WIDTH_SCALE"]),
        "h": ema["h"].update(raw_h * conf.EYES["BAR"]["HEIGHT_SCALE"]),
        "angle": ema["angle"].update(angle),
        "timestamp": time.time(),
    }


def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    """
    Draw the eye privacy bar.
    """

    ns = context.get("EYES")
    if not ns or not ns.get("data"):
        return frame

    bar = ns["data"]

    _draw_rotated_bar(
        frame,
        center=(int(bar["cx"]), int(bar["cy"])),
        size=(int(bar["w"]), int(bar["h"])),
        angle_deg=bar["angle"],
        color=conf.EYES["BAR"]["COLOR"],
        alpha=conf.EYES["BAR"]["ALPHA"],
    )

    return frame


# ------------------------------------------------------------
# Boilerplate lifecycle hooks
# ------------------------------------------------------------

def main(args, **kwargs):
    return True


def init(args, **kwargs):
    return True


def access(args, op, /, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None
