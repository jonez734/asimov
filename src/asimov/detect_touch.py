import cv2

MARGIN = 0  # No margin: fingertip must be inside the rect

def should_run(context):
    return "left_index_tip" in context and "rectangles" in context

def process(frame, context):
    fingertip = context["left_index_tip"]

    for rect in context["rectangles"]:
        polygon = rect["polygon"]
        dist = cv2.pointPolygonTest(polygon, fingertip, False)
        rect["touching"] = dist >= MARGIN

    return frame, context
