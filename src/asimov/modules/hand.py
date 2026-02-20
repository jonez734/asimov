# asimov/hand.py

"""
hand.py — authoritative hand detection module

Responsibilities:
- Own the HandDetector (cvzone / MediaPipe)
- Run detection exactly once per frame
- Publish raw hand geometry + metadata into context
- Optionally render overlays in draw()

Other modules (indexfingertip, pinch, gestures, etc.) must CONSUME
context['HAND'] and must NOT run their own hand detection.
"""

import time
import cv2
from cvzone.HandTrackingModule import HandDetector
from .. import io, conf
from ..common import ThreadSafeContext
import numpy as np

# Skeleton drawing is delegated to cvzone when overlays are enabled

# ---- Detection --------------------------------------------------------------

def detect(frame, context: ThreadSafeContext, **kwargs):
    try:
        if "HAND" not in context:
            cfg = conf.HAND.copy()

            context["HAND"] = {
                "cfg": cfg,
                "detector": HandDetector(
                    detectionCon=cfg["DETECTION_CON"],
                    maxHands=cfg["MAX_HANDS"],
                ),
                "hands": None,
                "overlay": None,
                "timestamp": None,
                "error_state": False,
            }

        ns = context["HAND"]
        ns["error_state"] = False

        cfg = ns["cfg"]
        detector = ns["detector"]

        hands, drawn = detector.findHands(frame, draw=False)
        ns["overlay"] = drawn
        ns["hands"] = hands or []
        ns["timestamp"] = time.time()

        context["HAND"] = ns

    except Exception:
        if "HAND" in context:
            context["HAND"]["error_state"] = True
        io.echo_traceback("Hand detection exception")


# ---- Drawing ----------------------------------------------------------------

def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    ns = context.get("HAND")
    if not ns:
        return frame

    if ns.get("error_state"):
        cv2.putText(frame, "HAND ERROR", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame

    cfg = ns["cfg"]

    # ---- cvzone-managed overlay (skeleton) ----
    if cfg.get("USE_OVERLAY"):
        overlay = ns.get("overlay")
        if overlay is not None:
            alpha = cfg.get("OVERLAY_ALPHA", 0.7)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    # ---- Optional text-only annotations ----
    hands = ns.get("hands") or []
    y_text = 30

    for hand in hands:
        if cfg.get("DRAW_HANDEDNESS") and "type" in hand:
            cv2.putText(frame, hand["type"], (10, y_text),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, cfg["TEXT_COLOR"], 2)
            y_text += 20

        if cfg.get("DRAW_CONFIDENCE") and "confidence" in hand:
            txt = f"conf: {hand['confidence']:.2f}"
            cv2.putText(frame, txt, (10, y_text),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, cfg["TEXT_COLOR"], 2)
            y_text += 20

    return frame


# ---- ui ------------------------------------------------------------------
def ui_schema(args=None, context=None) -> dict | None:
    return {
        "DETECTION": {
            "MIN_DETECTION_CONF": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Min Detection Confidence"
            },
            "MAX_HANDS": {
                "type": "int",
                "default": 1,
                "min": 1,
                "max": 4,
                "step": 1,
                "label": "Maximum Hands"
            }
        },

        "FILTER": {
            "FREQ": {
                "type": "float",
                "default": 0.30,
                "min": 1.0,
                "max": 240.0,
                "step": 1.0,
                "label": "Filter Frequency (Hz)"
            },
            "MIN_CUTOFF": {
                "type": "float",
                "default": 1.0,
                "min": 0.01,
                "max": 10.0,
                "step": 0.1,
                "label": "Min Cutoff"
            },
            "BETA": {
                "type": "float",
                "default": 0.0,
                "min": 0.0,
                "max": 5.0,
                "step": 0.05,
                "label": "Beta (Speed Sensitivity)"
            }
        },

        "DRAW": {
            "SHOW_LANDMARKS": {
                "type": "bool",
                "default": True,
                "label": "Draw Landmarks"
            },
            "SHOW_BBOX": {
                "type": "bool",
                "default": False,
                "label": "Draw Bounding Box"
            }
        },

        "DEBUG": {
            "SHOW_FPS": {
                "type": "bool",
                "default": False,
                "label": "Show Hand FPS"
            }
        }
    }

def initgui(args, root) -> bool:
    return True

# ---- Lifecycle hooks --------------------------------------------------------

def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
