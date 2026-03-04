# asimov/modules/rect.py

from typing import Dict, Tuple, List
import cv2
import numpy as np

from asimov import conf
from .rect_touch import CTX_TOUCHES

MODULE_NAME = "rect"

# Context keys
CTX_RECTS = "rects"


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
    Manage rectangles in context.
    Creates default rectangles if none exist.
    """
    rects: List[Dict] = context.get(CTX_RECTS, [])
    
    if not rects:
        init_default_rects(context)


def draw(frame: np.ndarray, context):
    """
    Draw rects and highlight touched ones.
    """

    rects: List[Dict] = context.get(CTX_RECTS, [])
    touches = set(context.get(CTX_TOUCHES, []))

    cfg = conf.RECT

    for rect in rects:
        x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
        rid = rect.get("id")

        touched = rid in touches

        color = cfg["TOUCHED_COLOR"] if touched else cfg["COLOR"]
        thickness = cfg["TOUCHED_THICKNESS"] if touched else cfg["THICKNESS"]

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
                cfg["LABEL_SCALE"],
                color,
                cfg["LABEL_THICKNESS"],
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


def init_default_rects(context):
    """Add default test rectangles to context."""
    add_rect(context, "test1", 100, 100, 100, 100)
    add_rect(context, "test2", 300, 100, 100, 100)
    add_rect(context, "test3", 500, 100, 100, 100)


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "DRAW": {
            "enabled": {
                "type": "bool",
                "default": True,
                "label": "Draw Rectangles"
            },
            "COLOR": {
                "type": "color",
                "default": [0, 180, 255],
                "label": "Rectangle Color (BGR)"
            },
            "TOUCHED_COLOR": {
                "type": "color",
                "default": [0, 0, 255],
                "label": "Touched Color (BGR)"
            },
            "THICKNESS": {
                "type": "int",
                "default": 2,
                "min": 1,
                "max": 10,
                "step": 1,
                "label": "Border Thickness"
            },
            "TOUCHED_THICKNESS": {
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 10,
                "step": 1,
                "label": "Touched Border Thickness"
            },
            "LABEL_SCALE": {
                "type": "float",
                "default": 0.5,
                "min": 0.1,
                "max": 2.0,
                "step": 0.1,
                "label": "Label Scale"
            },
            "LABEL_THICKNESS": {
                "type": "int",
                "default": 1,
                "min": 1,
                "max": 5,
                "step": 1,
                "label": "Label Thickness"
            },
        }
    }


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
