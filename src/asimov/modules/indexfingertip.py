import time
import cv2
from .. import io, conf
from ..base.common import ThreadSafeContext, OneEuroFilter
from ..base.util import draw_text
import numpy as np

# MediaPipe landmark index
INDEX_FINGER_TIP_LM = 8

# Finger-up pattern from cvzone semantics
INDEX_UP_PATTERN = [0, 1, 0, 0, 0]

ERR_TEXT_ORG = (10, 30)
ERR_TEXT_SCALE = 0.6
ERR_TEXT_THICKNESS = 2


def detect(frame, context: ThreadSafeContext, **kwargs):
    if_conf = conf.get("INDEXFINGERTIP", {})
    try:
        # ---- Init -----------------------------------------------------------
        if "INDEXFINGERTIP" not in context:
            f_params = if_conf.get("FILTER", {})
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
        f_params = if_conf.get("FILTER", {})
        filter_enabled = f_params.get("enabled", True)
        alpha = f_params.get("alpha", 0.4)
        deadzone = f_params.get("deadzone", 2)

        ns["error_state"] = False
        ns["active"] = False
        ns["data"] = None

        debug = if_conf.get("DEBUG", {}).get("enabled", False)

        # ---- Consume HAND module -------------------------------------------
        hand_ns = context.get("HAND")
        if not hand_ns or not hand_ns.get("hands"):
            if debug:
                io.echo("Indexfingertip: no hand detected", level="debug")
            return

        hand = hand_ns["hands"][0]
        if debug:
            io.echo(f"Indexfingertip: hand keys={list(hand.keys())}", level="debug")

        # Skip confidence check if not provided by cvzone (cvzone doesn't always include it)
        detection_con = hand.get("confidence", hand.get("detectionCon", None))
        if detection_con is not None:
            min_conf = if_conf.get("DETECTION", {}).get("DETECTION_CON", 0.5)
            if detection_con < min_conf:
                if debug:
                    io.echo(
                        f"Indexfingertip: low conf {detection_con:.2f} < {min_conf}",
                        level="debug",
                    )
                return

        # cvzone finger state (geometry-only, no detection)
        fingers = hand_ns["detector"].fingersUp(hand)
        if debug:
            io.echo(f"Indexfingertip: fingers={fingers}", level="debug")
        # Only require index finger up (index 1), not strict pattern match
        if fingers[1] != 1:
            if debug:
                io.echo("Indexfingertip: index finger not up", level="debug")
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

        if debug:
            io.echo(
                f"Indexfingertip: detected at ({smooth_x:.0f}, {smooth_y:.0f})",
                level="debug",
            )

        context["INDEXFINGERTIP"] = ns

    except Exception:
        if "INDEXFINGERTIP" in context:
            context["INDEXFINGERTIP"]["error_state"] = True
        io.echo_traceback("Indexfingertip detect exception")


def draw(frame, context: ThreadSafeContext, /, config=None, **kwargs) -> np.ndarray:
    if_conf = conf.get("INDEXFINGERTIP", {})
    if not if_conf.get("DRAW", {}).get("enabled", True):
        return frame

    debug = if_conf.get("DEBUG", {}).get("enabled", False)

    ns = context.get("INDEXFINGERTIP")
    if not ns:
        if debug:
            io.echo("Indexfingertip draw: no context", level="debug")
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
        if debug:
            io.echo("Indexfingertip draw: not active", level="debug")
        return frame

    data = ns.get("data")
    if not data:
        if debug:
            io.echo("Indexfingertip draw: no data", level="debug")
        return frame

    if debug:
        io.echo(
            f"Indexfingertip draw: at ({data['x']:.0f}, {data['y']:.0f})", level="debug"
        )

    draw_conf = if_conf.get("DRAW", {})
    radius = draw_conf.get("radius", 6)
    color = draw_conf.get("color", (0, 255, 0))
    thickness = draw_conf.get("thickness", -1)
    cv2.circle(
        frame,
        (int(data["x"]), int(data["y"])),
        radius,
        color,
        thickness,
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
            "enabled": {
                "type": "bool",
                "default": False,
                "label": "Enable Debug Output",
            },
            "SHOW_TRAIL": {
                "type": "bool",
                "default": False,
                "label": "Show Motion Trail",
            },
        },
    }


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def get_stateful_keys() -> list[str]:
    """Return list of context keys this module manages."""
    return ["INDEXFINGERTIP"]


def main(args, **kwargs):
    return True
