import numpy as np

def should_run(context):
    # Only run if there are trackers to update
    return len(context.get("trackers", [])) > 0

def process(frame, context):
    new_trackers = []
    updated_rects = []

    for tracker, rect_id, _ in context.get("trackers", []):
        success, box = tracker.update(frame)
        if success:
            x, y, w, h = [int(v) for v in box]
            polygon = np.array([
                [[x, y]],
                [[x + w, y]],
                [[x + w, y + h]],
                [[x, y + h]],
            ])
            updated_rects.append({
                "polygon": polygon,
                "touching": False,
                "id": rect_id
            })
            new_trackers.append((tracker, rect_id, box))

    context["trackers"] = new_trackers
    context["rectangles"] = updated_rects
    return frame, context
