import cv2

def should_run(context):
    return "rectangles" in context

def process(frame, context):
    rectangles = context.get("rectangles", [])
    index_tip = context.get("index_tip", None)

    MARGIN = 0  # touch margin in pixels
    # print(f"{index_tip=}")
    if index_tip:
        cv2.circle(frame, index_tip, 8, (0, 255, 255), -1)

    for rect in rectangles:
        polygon = rect["polygon"].reshape((-1, 1, 2))  # shape for polylines

        # Check touch
        touching = False
        if index_tip is not None:
            dist = cv2.pointPolygonTest(polygon, index_tip, False)
            if dist >= -MARGIN:
                touching = True

        rect["touching"] = touching

        color = (0, 255, 0) if touching else (0, 0, 255)
        thickness = 3

        cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=thickness)

    return frame, context
