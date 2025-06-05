import cv2
import time
import numpy as np

REFRESH_INTERVAL = 2.5  # seconds

last_refresh_time = 0

def should_run(context):
    global last_refresh_time
    now = time.time()
    return now - last_refresh_time >= REFRESH_INTERVAL

def process(frame, context):
    global last_refresh_time
    now = time.time()
    last_refresh_time = now

    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 1)
    img_canny = cv2.Canny(img_blur, 50, 150)
    contours, _ = cv2.findContours(img_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectangles = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= 1000:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                rect = {
                    "polygon": approx.reshape((4, 2)),
                    "last_seen": now,
                    "touching": False  # this will be updated in draw_overlays
                }
                rectangles.append(rect)

    context["rectangles"] = rectangles
    return frame, context
