# asimov/modules/rect_touch.py

from typing import Dict, Tuple, List
import numpy as np

from .. import conf
from ..base.common import ThreadSafeContext

CTX_RECTS = "rects"
CTX_TOUCHES = "rect_touches"


def _point_in_rect(pt: Tuple[int, int], rect: Dict) -> bool:
    x, y = pt
    rx, ry, rw, rh = rect["x"], rect["y"], rect["w"], rect["h"]
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    """
    Detect index fingertip touching rects.
    Reads rectangles from context, checks if fingertip is inside.
    """

    cfg = conf.get("RECT_TOUCH").get("DETECTION", {})
    if not cfg.get("enabled", True):
        context[CTX_TOUCHES] = []
        return

    rects: List[Dict] = context.get(CTX_RECTS, [])

    if not rects:
        context[CTX_TOUCHES] = []
        return

    fingertip_ns = context.get("INDEXFINGERTIP")

    touches: List[str] = []

    if fingertip_ns and fingertip_ns.get("active"):
        data = fingertip_ns.get("data")
        if data:
            pt = (int(data["x"]), int(data["y"]))

            for rect in rects:
                if _point_in_rect(pt, rect):
                    touches.append(rect.get("id", "unknown"))

    context[CTX_TOUCHES] = touches


def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    """
    Rect_touch only detects touches - drawing handled by rect module.
    """
    return frame


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "DETECTION": {
            "enabled": {
                "type": "bool",
                "default": True,
                "label": "Enable Touch Detection",
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
