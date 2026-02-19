import time
import cv2
from .. import io, conf
from ..common import ThreadSafeContext, OneEuroFilter
import numpy as np

# MediaPipe landmark index
INDEX_FINGER_TIP_LM = 8

# Finger-up pattern from cvzone semantics
INDEX_UP_PATTERN = [0, 1, 0, 0, 0]

ERR_TEXT_ORG = (10, 30)
ERR_TEXT_SCALE = 0.6
ERR_TEXT_THICKNESS = 2

def detect(frame, context: ThreadSafeContext, **kwargs):
    try:
        # ---- Init -----------------------------------------------------------
        if "INDEXFINGERTIP" not in context:
            f_params = conf.INDEXFINGERTIP["FILTER"]
            context["INDEXFINGERTIP"] = {
                "ema": {
                    "x": OneEuroFilter(
                        freq=f_params["FREQ"],
                        min_cutoff=f_params["MIN_CUTOFF"],
                        beta=f_params["BETA"],
                    ),
                    "y": OneEuroFilter(
                        freq=f_params["FREQ"],
                        min_cutoff=f_params["MIN_CUTOFF"],
                        beta=f_params["BETA"],
                    ),
                },
                "active": False,
                "data": None,
                "error_state": False,
            }

        ns = context["INDEXFINGERTIP"]
        ns["error_state"] = False
        ns["active"] = False
        ns["data"] = None

        # ---- Consume HAND module -------------------------------------------
        hand_ns = context.get("HAND")
        if not hand_ns or not hand_ns.get("hands"):
            return

        hand = hand_ns["hands"][0]

        # cvzone finger state (geometry-only, no detection)
        fingers = hand_ns["detector"].fingersUp(hand)
        if fingers != INDEX_UP_PATTERN:
            return

        # ---- Extract + smooth ----------------------------------------------
        raw_x, raw_y = hand["lmList"][INDEX_FINGER_TIP_LM][:2]

        ns["data"] = {
            "x": ns["ema"]["x"].update(raw_x),
            "y": ns["ema"]["y"].update(raw_y),
            "timestamp": time.time(),
        }
        ns["active"] = True

        context["INDEXFINGERTIP"] = ns

    except Exception:
        if "INDEXFINGERTIP" in context:
            context["INDEXFINGERTIP"]["error_state"] = True
        io.echo_traceback("Indexfingertip detect exception")


def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    ns = context.get("INDEXFINGERTIP")
    if not ns:
        return frame

    if ns.get("error_state"):
        cv2.putText(
            frame,
            "INDEXFINGERTIP ERROR",
            ERR_TEXT_ORG,
            cv2.FONT_HERSHEY_SIMPLEX,
            ERR_TEXT_SCALE,
            (0, 0, 255),
            ERR_TEXT_THICKNESS,
        )
        return frame

    if not ns.get("active"):
        return frame

    data = ns.get("data")
    if not data:
        return frame

    cv2.circle(
        frame,
        (int(data["x"]), int(data["y"])),
        conf.INDEXFINGERTIP.get("CIRCLE_RADIUS", 10),
        conf.INDEXFINGERTIP.get("COLOR", (0, 255, 0)),
        cv2.FILLED,
    )

    return frame

def ui_schema(args=None, context=None) -> dict | None:
    return {
        "FILTER": {
            "FREQ": {
                "type": "float",
                "default": 30.0,
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
                "label": "Beta"
            }
        },

        "POINTER": {
            "ENABLED": {
                "type": "bool",
                "default": True,
                "label": "Enable Pointer"
            },
            "RADIUS": {
                "type": "int",
                "default": 8,
                "min": 1,
                "max": 50,
                "step": 1,
                "label": "Pointer Radius"
            },
            "COLOR": {
                "type": "color",
                "default": [0, 255, 0],  # BGR
                "label": "Pointer Color (BGR)"
            },
            "ALPHA": {
                "type": "float",
                "default": 0.8,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Pointer Opacity"
            }
        },

        "GESTURE": {
            "PINCH_ENABLED": {
                "type": "bool",
                "default": False,
                "label": "Enable Pinch Detection"
            },
            "PINCH_THRESHOLD": {
                "type": "float",
                "default": 0.05,
                "min": 0.001,
                "max": 0.2,
                "step": 0.005,
                "label": "Pinch Activation Threshold"
            }
        },

        "DEBUG": {
            "SHOW_TRAIL": {
                "type": "bool",
                "default": False,
                "label": "Show Motion Trail"
            }
        }
    }

def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
