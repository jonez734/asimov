import time
# import locale
import argparse

from bbsengine6 import io

import cv2
import pyvirtualcam
import numpy as np

import mediapipe as mp

from asimov.util import draw_text, get_device_by_label
from asimov import conf, glitch

# Constants
MARGIN = 20  # pixels
TITLE = "Project Asimov v202508.0"

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

from cvzone.HandTrackingModule import HandDetector

# Create hand detector instance
detector = HandDetector(detectionCon=0.8, maxHands=2)

index_finger_tip = None

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)

# Eye landmark indices (same as before)
LEFT_EYE_IDX = [33, 133, 159, 145, 160, 158, 153, 144]
RIGHT_EYE_IDX = [362, 263, 386, 374, 385, 380, 373, 390]

def overlay_eyes(frame):
    results = face_mesh.process(frame)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            ih, iw, _ = frame.shape

            # Get eye coordinates
            left_eye_points = [(int(face_landmarks.landmark[i].x * iw), int(face_landmarks.landmark[i].y * ih)) for i in LEFT_EYE_IDX]
            right_eye_points = [(int(face_landmarks.landmark[i].x * iw), int(face_landmarks.landmark[i].y * ih)) for i in RIGHT_EYE_IDX]

            # Combine all eye points
            all_eye_points = left_eye_points + right_eye_points
            all_eye_points_np = np.array(all_eye_points)

            # Get bounding rectangle around both eyes
            x, y, w, h = cv2.boundingRect(all_eye_points_np)

            # Make the rectangle a bit taller to give that "witness protection" look
            y -= int(0.2 * h)
            h += int(0.4 * h)

            # Draw the blue rectangle (privacy bar)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), thickness=-1)
    return frame

def overlay_fingertip(frame):
    global index_finger_tip, detector

    # Detect hands and get list of hands and image with drawing
    hands, frame = detector.findHands(frame, draw=False)
    index_finger_tip = None

    if hands:
        for hand in hands:
            fingers = detector.fingersUp(hand)
            if fingers == [0, 1, 0, 0, 0]:  # Only index finger is up
                # Get index finger tip position (landmark 8)
                index_finger_tip = tuple(hand['lmList'][8][:2])  # x, y
                cv2.circle(frame, index_finger_tip, 8, (0, 255, 255), -1)

    return frame

def detect_rectangles(frame):
    detected = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 1)
    canny = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1000:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                polygon = approx.reshape((4, 2))
                detected.append(polygon)
    return detected

def draw_rectangles(frame, rectangles):
    global index_finger_tip
    for polygon in rectangles:
        poly_np = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
        touching = False
        if index_finger_tip:
            dist = cv2.pointPolygonTest(poly_np, index_finger_tip, False)
            if dist >= -MARGIN:
                touching = True

        color = (0, 255, 0) if touching else (255, 0, 0)
        cv2.polylines(frame, [poly_np], True, color, 2)
    return frame

def overlay_rectangles(frame):
    rectangles = detect_rectangles(frame)
    return draw_rectangles(frame, rectangles)

def overlay_watermark(frame):
    return draw_text(frame, 10, 15, TITLE, color=(255, 255, 255), font_scale=0.50, alpha=0.75, shadow_alpha=0.75, shadow_offset=2)

def overlay_glitches(frame):
    glitch.scheduler()
    return glitch.apply(frame)

def camera_ready(cap, timeout=5):
    start_time = time.time()
    while True:
        ret, frame = cap.read()
        if frame is not None:
            return True  # Camera gave a valid frame
        print("waiting...")
        if time.time() - start_time >= timeout:
            print("camera_ready(): timeout")
            return False  # Timeout reached, return failure
        time.sleep(0.1)  # Avoid busy waiting

OVERLAYS = [
            { "key": "f", "enabled":True, "running":True,  "label": "fingertip", "func": overlay_fingertip},
            { "key": "r", "enabled":True, "running":True,  "label": "rects",     "func": overlay_rectangles},
            { "key": "g", "enabled":True, "running":False, "label": "glitches",  "func": overlay_glitches},
            { "key": "w", "enabled":True, "running":True,  "label": "watermark", "func": overlay_watermark},
            { "key": "e", "enabled":True, "running":True,  "label": "eyes",      "func": overlay_eyes},

        ]

def apply_overlays(frame):
    global OVERLAYS

    for o in OVERLAYS:
        if not o["enabled"]:
            continue
        if not o["running"]:
            continue
        f = o.get("func", None)
#        io.echo(f"checking {f=}", level="debug")
        if callable(f):
#            io.echo(f"calling {f=}", level="debug")
            frame = o["func"](frame)
    return frame


def main(args, **kwargs):
    global OVERLAYS

    # Open the real webcam
    cap = cv2.VideoCapture(conf.CAP_DEVICE)

    try:

        # Make sure the webcam opens correctly
        if not cap.isOpened():
            raise RuntimeError("Could not open webcam. check group membership.")

        if camera_ready(cap) is False:
            raise RuntimeError("Camera is not ready after 5s")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)
        if cap.set(cv2.CAP_PROP_FPS, CAP_FPS) is False:
            io.echo(f"could not set FPS to {conf.FPS}")

        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)

        # Get the frame size
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from webcam")

        # get virtual camera device by label
        device = get_device_by_label(conf.CAM_LABEL)
##        io.echo(f"{{labelcolor}}virtualcam label {{valuecolor}}{conf.CAM_LABEL} {{labelcolor}}, device {{valuecolor}}{device}{{/all}}")
        # Start the virtual camera
        with pyvirtualcam.Camera(width=actual_width, height=actual_height, fps=actual_fps, print_fps=False, device=device) as cam:
            io.echo(f"{{labelcolor}}Capture: {{valuecolor}}{conf.CAP_DEVICE}, virtcam: ({cam.device}) {actual_width}{{labelcolor}}x{{valuecolor}}{actual_height} {{labelcolor}}@ {{valuecolor}}{actual_fps} {{labelcolor}}fps{{/all}}")
            while True:
                ret, frame = cap.read()
                if frame is None:
                    continue

                height, width = frame.shape[:2]

                if not ret:
                    break

                frame = cv2.flip(frame, 1)

                frame = apply_overlays(frame)

                cv2.imshow(TITLE, frame) # BGR

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Send frame to virtual camera
                cam.send(frame)

                ch = cv2.waitKey(10) & 0xFF
                for o in OVERLAYS:
                    if ch == ord(o["key"]):
                        print(f"toggle {o=}")
                        o["running"] = True - o["running"]
                        break

                if ch == ord("q") or ch == 27:
                    break

                # Wait until next frame is due
                cam.sleep_until_next_frame()
    finally:
        cap.release()

def buildargs(args=None, **kw:dict):
    parser = argparse.ArgumentParser("asimov")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

#    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
#    database.buildargs(parser, defaults, suppress=True)

    return parser

if __name__ == "__main__":
#    locale.setlocale(locale.LC_ALL, "")
    time.tzset()
    args = buildargs()

    try:
        main(args)
    except KeyboardInterrupt:
        io.echo("{/all}*INTR*")
    except EOFError:
        io.echo("{/all}*EOF*")
    finally:
        io.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (io.getterminalheight()))
