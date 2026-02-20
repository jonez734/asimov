# asimov/modules/rect.py

from typing import Dict, Tuple, List
import cv2
import numpy as np

from . import conf

MODULE_NAME = "rect"

# Context keys
CTX_RECTS = "rects"
CTX_TOUCHES = "rect_touches"


# ------------------------
# Rect utilities
# ------------------------

def _point_in_rect(pt: Tuple[int, int], rect: Dict) -> bool:
    x, y = pt
    rx, ry, rw, rh = rect["x"], rect["y"], rect["w"], rect["h"]
    return rx <= x <= rx + rw and ry <= y <= ry + rh


# ------------------------
# Module API
# ------------------------

def detect(frame: np.ndarray, context):
    """
    Detect index fingertip touching rects.
    """

    rects: List[Dict] = context.get(CTX_RECTS, [])
    fingertip = context.get("indexfingertip")

    touches: List[str] = []

    if fingertip:
        pt = (fingertip["x"], fingertip["y"])

        for rect in rects:
            if _point_in_rect(pt, rect):
                touches.append(rect.get("id", "unknown"))

    context[CTX_TOUCHES] = touches


def draw(frame: np.ndarray, context):
    """
    Draw rects and highlight touched ones.
    """

    rects: List[Dict] = context.get(CTX_RECTS, [])
    touches = set(context.get(CTX_TOUCHES, []))

    for rect in rects:
        x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
        rid = rect.get("id")

        touched = rid in touches

        color = conf.RECT_TOUCHED_COLOR if touched else conf.RECT_COLOR
        thickness = (
            conf.RECT_TOUCHED_THICKNESS
            if touched
            else conf.RECT_THICKNESS
        )

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            color,
            thickness,
        )

        if rid:
            cv2.putText(
                frame,
                rid,
                (x + 4, y - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                conf.RECT_LABEL_SCALE,
                color,
                conf.RECT_LABEL_THICKNESS,
                cv2.LINE_AA,
            )


def state(context) -> Dict:
    """
    Minimal introspection hook.
    """

    return {
        "rect_count": len(context.get(CTX_RECTS, [])),
        "active_touches": context.get(CTX_TOUCHES, []),
    }


# ------------------------
# Optional helpers
# ------------------------

def add_rect(context, rect_id: str, x: int, y: int, w: int, h: int):
    rects = context.setdefault(CTX_RECTS, [])
    rects.append(
        {
            "id": rect_id,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
        }
    )

def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
