import cv2
import cvzone
import numpy as np
from .. import conf
from ..common import ThreadSafeContext

ERR_TEXT_ORG = (10, 30)
ERR_TEXT_SCALE = 0.6
ERR_TEXT_THICKNESS = 2


def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    fps_data = context.get("FPS")
    if not fps_data:
        return frame

    draw_conf = conf.FPS_OVERLAY.get("DRAW", {})
    if not draw_conf.get("enabled", True):
        return frame

    pos = draw_conf.get("pos", (10, 30))
    bg_color = tuple(draw_conf.get("bg_color", [255, 0, 255]))
    text_color = tuple(draw_conf.get("text_color", [255, 255, 255]))
    scale = draw_conf.get("scale", 1.5)
    thickness = draw_conf.get("thickness", 2)

    logic_fps = fps_data.get("logic", 0)
    render_fps = fps_data.get("render", 0)

    cvzone.putTextRect(
        frame,
        f"Logic FPS: {int(logic_fps)}",
        pos=pos,
        scale=scale,
        thickness=thickness,
        colorT=text_color,
        colorR=bg_color,
        offset=10
    )

    cvzone.putTextRect(
        frame,
        f"Render FPS: {int(render_fps)}",
        pos=(pos[0], pos[1] + 40),
        scale=scale,
        thickness=thickness,
        colorT=text_color,
        colorR=bg_color,
        offset=10
    )

    return frame


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "DRAW": {
            "enabled": {
                "type": "bool",
                "default": True,
                "label": "Show FPS Overlay"
            },
            "pos": {
                "type": "string",
                "default": "10,30",
                "label": "Position (x,y)"
            },
            "bg_color": {
                "type": "color",
                "default": [255, 0, 255],
                "label": "Background Color (BGR)"
            },
            "text_color": {
                "type": "color",
                "default": [255, 255, 255],
                "label": "Text Color (BGR)"
            },
            "scale": {
                "type": "float",
                "default": 1.5,
                "min": 0.5,
                "max": 5.0,
                "step": 0.1,
                "label": "Text Scale"
            },
            "thickness": {
                "type": "int",
                "default": 2,
                "min": 1,
                "max": 5,
                "step": 1,
                "label": "Text Thickness"
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
