import cv2

from . import conf

def detect(frame, context):
    fingertip = context.get("fingertip", None)

    rectangles = context.get("rectangles", None)
    if rectangles:
        for rect in rectangles:
            polygon = rect["polygon"]
            dist = cv2.pointPolygonTest(polygon, fingertip, False)
            rect["touched"] = dist >= conf.RECT_TOUCH_MARGIN
            if not rect["touched"]:
                rect["bordercolor"] = conf.RECT_BORDER_COLOR # (255, 0,0)
            else:
                rect["bordercolor"] = conf.RECT_BORDER_COLOR_TOUCHED # (0, 255, 0)

    return frame, context
