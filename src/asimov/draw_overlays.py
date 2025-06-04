import cv2

def should_run(context):
    return "rectangles" in context

def process(frame, context):
    for rect in context["rectangles"]:
        color = (0, 255, 0) if rect.get("touching") else (0, 0, 255)
        polygon = rect["polygon"]
        cv2.polylines(frame, [polygon], isClosed=True, color=color, thickness=2)

        # Optionally show ID (if present)
        if "id" in rect:
            x, y = polygon[0][0]
            cv2.putText(frame, f"ID {rect['id']}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Also visualize fingertip if available
    if "left_index_tip" in context:
        tip = context["left_index_tip"]
        cv2.circle(frame, tip, 8, (255, 255, 255), -1)  # Outer circle
        cv2.circle(frame, tip, 4, (0, 255, 255), -1)    # Inner circle

    return frame, context
