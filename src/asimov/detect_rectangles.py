import cv2
import time

REFRESH_INTERVAL = 1.5  # seconds

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
    img_blur = img_gray  # cv2.GaussianBlur(img_gray, (5, 5), 1)
    img_canny = cv2.Canny(img_blur, 50, 150)
    cv2.imshow("img_canny", img_canny)
    contours, _ = cv2.findContours(
        img_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    rectangles = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= 1000:
            peri = cv2.arcLength(cnt, True)
            epsilon = 0.02 * peri
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            print(f"{approx=}")
            # Draw the detected rectangle on the frame
            cv2.drawContours(frame, [approx], -1, (0, 255, 0), 3)

            if len(approx) == 4:
                # Ensure the contour is convex and has a reasonable aspect ratio
                # This helps filter out non-rectangular shapes that might have 4 points
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / h
                # Adjust these thresholds as needed for your specific use case
                if 0.6 < aspect_ratio < 1.0 and cv2.isContourConvex(approx):
                    rect = {
                        "polygon": approx.reshape((4, 2)),
                        "last_seen": now,
                        "touching": False,
                    }
                    rectangles.append(rect)

    context["rectangles"] = rectangles
    return frame, context
