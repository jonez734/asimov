import cv2
import time

prev_time = 0


def should_run(context):
    # Always run this module
    return True


def process(frame, context):
    global prev_time
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time else 0
    prev_time = curr_time

    # Compose status string
    flags = []
    if context.get("distortions_enabled"):
        flags.append("D")

    status_text = f"FPS: {fps:.1f} {' '.join(flags)}"

    # Draw background rectangle for text readability
    cv2.rectangle(frame, (5, 5), (170, 30), (0, 0, 0), -1)

    # Draw text in green
    cv2.putText(
        frame, status_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
    )

    return frame, context
