from cv2 import pointPolygonTest
from . import conf

##from .conf import RECT_COLOR_TOUCHED, RECT_COLOR, RECT_TOUCH_MARGIN

def should_run(context):
    return "index_finger_tip" in context and "rectangles" in context

def detect(frame, context):
    fingertip = context.get("fingertip", None);

    for rect in context["rectangles"]:
        polygon = rect["polygon"]
        dist = pointPolygonTest(polygon, fingertip, False)
        rect["touched"] = dist >= conf.RECT_TOUCH_MARGIN
        if not rect["touched"]:
            rect["bordercolor"] = conf.RECT_COLOR # (255, 0,0)
        else:
            rect["bordercolor"] = conf.RECT_COLOR_TOUCHED # (0, 255, 0)

    return frame, context
