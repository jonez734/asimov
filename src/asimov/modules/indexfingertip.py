import time
import cv2
from asimov import io
from asimov import conf
from asimov.base.common import ThreadSafeContext, OneEuroFilter
from asimov.base.util import draw_text
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
                "prev": {},
            }

        ns = context["INDEXFINGERTIP"]
        f_params = conf.INDEXFINGERTIP["FILTER"]
        filter_enabled = f_params.get("enabled", True)
        alpha = f_params.get("alpha", 0.4)
        deadzone = f_params.get("deadzone", 2)

        ns["error_state"] = False
        ns["active"] = False
        ns["data"] = None

        # ---- Consume HAND module -------------------------------------------
        hand_ns = context.get("HAND")
        if not hand_ns or not hand_ns.get("hands"):
            return

        hand = hand_ns["hands"][0]

        # Check detection confidence
        detection_con = hand.get("detectionCon", 0)
        if detection_con < conf.INDEXFINGERTIP.get("DETECTION", {}).get(
            "DETECTION_CON", 0.6
        ):
            return

        # cvzone finger state (geometry-only, no detection)
        fingers = hand_ns["detector"].fingersUp(hand)
        if fingers != INDEX_UP_PATTERN:
            return

        # ---- Extract + smooth ----------------------------------------------
        raw_x, raw_y = hand["lmList"][INDEX_FINGER_TIP_LM][:2]

        if filter_enabled:
            one_euro_x = ns["ema"]["x"].update(raw_x)
            one_euro_y = ns["ema"]["y"].update(raw_y)
        else:
            one_euro_x = raw_x
            one_euro_y = raw_y

        prev = ns.get("prev", {})
        prev_x = prev.get("x", one_euro_x)
        prev_y = prev.get("y", one_euro_y)

        dx = one_euro_x - prev_x
        dy = one_euro_y - prev_y
        if abs(dx) < deadzone:
            one_euro_x = prev_x
        if abs(dy) < deadzone:
            one_euro_y = prev_y

        if alpha > 0:
            smooth_x = alpha * one_euro_x + (1 - alpha) * prev_x
            smooth_y = alpha * one_euro_y + (1 - alpha) * prev_y
        else:
            smooth_x = one_euro_x
            smooth_y = one_euro_y

        ns["prev"] = {"x": smooth_x, "y": smooth_y}

        ns["data"] = {
            "x": smooth_x,
            "y": smooth_y,
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

    if not conf.INDEXFINGERTIP.get("DRAW", {}).get("enabled", True):
        return frame

    if ns.get("error_state"):
        frame = draw_text(
            frame,
            ERR_TEXT_ORG[0],
            ERR_TEXT_ORG[1],
            "INDEXFINGERTIP ERROR",
            color=(0, 0, 255),
            font_scale=ERR_TEXT_SCALE,
            thickness=ERR_TEXT_THICKNESS,
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
        conf.INDEXFINGERTIP["DRAW"]["radius"],
        conf.INDEXFINGERTIP["DRAW"]["color"],
        conf.INDEXFINGERTIP["DRAW"]["thickness"],
    )

    return frame


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "DETECTION": {
            "DETECTION_CON": {
                "type": "float",
                "default": 0.6,
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "label": "Detection Confidence",
            },
        },
        "FILTER": {
            "enabled": {"type": "bool", "default": True, "label": "Enable Filter"},
            "alpha": {
                "type": "float",
                "default": 0.4,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Smoothing Factor",
            },
            "deadzone": {
                "type": "int",
                "default": 2,
                "min": 0,
                "max": 20,
                "step": 1,
                "label": "Deadzone (pixels)",
            },
            "FREQ": {
                "type": "float",
                "default": 30.0,
                "min": 1.0,
                "max": 240.0,
                "step": 1.0,
                "label": "Filter Frequency (Hz)",
            },
            "MIN_CUTOFF": {
                "type": "float",
                "default": 1.0,
                "min": 0.01,
                "max": 10.0,
                "step": 0.1,
                "label": "Min Cutoff",
            },
            "BETA": {
                "type": "float",
                "default": 0.0,
                "min": 0.0,
                "max": 5.0,
                "step": 0.05,
                "label": "Beta",
            },
        },
        "DRAW": {
            "enabled": {"type": "bool", "default": True, "label": "Draw Pointer"},
            "radius": {
                "type": "int",
                "default": 6,
                "min": 1,
                "max": 50,
                "step": 1,
                "label": "Pointer Radius",
            },
            "color": {
                "type": "color",
                "default": [0, 255, 0],
                "label": "Pointer Color (BGR)",
            },
            "thickness": {
                "type": "int",
                "default": -1,
                "min": -1,
                "max": 10,
                "step": 1,
                "label": "Thickness (-1=filled)",
            },
        },
        "DEBUG": {
            "SHOW_TRAIL": {
                "type": "bool",
                "default": False,
                "label": "Show Motion Trail",
            }
        },
    }


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
