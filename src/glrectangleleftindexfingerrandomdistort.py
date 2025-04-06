import random
import time
import threading

import cv2
import numpy as np

from OpenGL.GL import *

from flask import Flask, Response

import glfw

from cvzone.HandTrackingModule import HandDetector

import asimov.util

# Global variables
#texture_id = None
apply_distortion = False
next_distortion_time = time.time() + random.uniform(2, 5)

# OpenCV video capture
#cap = cv2.VideoCapture(0)
detector = HandDetector(detectionCon=0.8, maxHands=2)

MARGIN = 10

class VideoCaptureThread(threading.Thread):
    def __init__(self, src=0, width=800, height=600):
        super().__init__()
        self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.running = True
        self.frame = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame

    def get_frame(self):
        with self.lock:
            return self.frame

    def stop(self):
        self.running = False
        self.thread.join()
        self.cap.release()

class FlaskThread(threading.Thread):
    app = Flask(__name__)

    def __init__(self, vct):
        self.running = True

        self.vct = vct
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        self.app.add_url_rule('/video_feed', 'video_feed', self.video_feed)

    def run(self):
        self.app.run(host='0.0.0.0', port=5000, threaded=True, debug=True, use_reloader=False)

    def generate_frames(self):
        while self.running:
            frame = self.vct.get_frame() # success, frame = cap.read()
            if frame is None:
                time.sleep(0.25)
                continue

            # Optional: Process frame with OpenGL (You can integrate PyOpenGL here)

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def video_feed(self):
        return Response(self.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def stop(self):
        self.running = False
#        self.thread.join()

def update_texture(textureid, image):
    glBindTexture(GL_TEXTURE_2D, textureid)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.shape[1], image.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, image)
    glBindTexture(GL_TEXTURE_2D, 0)

def apply_random_distortion(image):
    choice = random.choice(['desaturate', 'oversaturate', 'color_shift', 'contrast', 'whitenoise', 'tearing'])
    print(f"{choice=}")
    if choice == 'desaturate':
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif choice == 'oversaturate':
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        hsv[..., 1] = np.clip(hsv[..., 1] * 2.0, 0, 255)
        image = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    elif choice == 'color_shift':
        b, g, r = cv2.split(image)
        image = cv2.merge([g, r, b])
    elif choice == 'contrast':
        alpha = random.uniform(0.5, 1.5)
        image = cv2.convertScaleAbs(image, alpha=alpha, beta=0)
    elif choice == 'whitenoise':
        intensity = random.randint(32, 128)
        noise = np.random.randint(0, intensity, image.shape, dtype='uint8')
        image = cv2.add(image, noise)
    elif choice == 'tearing':
        image = tearing_effect(image)
    return image

def processframe(img):
    global detector
    # Hand detection
    hands, img = detector.findHands(img, draw=False)

    left_index_tip = None
    if hands:
        for hand in hands:
            if hand['type'] == "Left":
                lmList = hand['lmList']
                left_index_tip = (lmList[8][0], lmList[8][1])  # Index fingertip (landmark 8)

    # Rectangle detection
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
    imgCanny = cv2.Canny(imgBlur, 50, 150)
    contours, _ = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectangles = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= 1000:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

            if len(approx) == 4:
                pts = approx.reshape((4, 2))
                polygon = np.array(pts, np.int32).reshape((-1, 1, 2))

                # Check if fingertip is inside or near the rectangle (with margin)
                touching = False
                if left_index_tip is not None:
                    dist = cv2.pointPolygonTest(polygon, left_index_tip, False)

                    # Debugging print statements
                    print(f"Fingertip: {left_index_tip}, Polygon: {pts}, Dist: {dist}")

                    # Use margin to check proximity to the polygon
                    if dist >= -MARGIN:
                        touching = True

                rectangles.append((polygon, touching))

    # Draw rectangles first
    for polygon, touching in rectangles:
        # Set color based on whether fingertip is touching
        color = (0, 255, 0) if not touching else (0, 0, 255)  # Green if not touching, Red if touching
        cv2.polylines(img, [polygon], True, color, 2)

    # Draw fingertip marker on top!
    if left_index_tip is not None:
        cv2.circle(img, left_index_tip, 8, (0, 255, 255), cv2.FILLED)
        cv2.circle(img, left_index_tip, 12, (0, 255, 255), 2)
    
    return img

def tearing_effect(image):
    rows, cols, _ = image.shape
    num_slices = random.randint(3, 8)  # number of tearing "slices"
    tear_image = image.copy()

    for _ in range(num_slices):
        y = random.randint(0, rows - 20)
        h = random.randint(5, 20)  # height of tear band
        shift = random.randint(-30, 30)  # how much to horizontally offset

        # Shift the band horizontally
        tear_image[y:y+h, :] = np.roll(tear_image[y:y+h, :], shift, axis=1)

        # Add a thin black line above or below to simulate a gap
        gap_position = y + h if (y + h) < rows else y - 1
        gap_thickness = random.randint(1, 3)
        gap_color = random.randint(0, 30)  # very dark gray instead of pure black
        if 0 <= gap_position < rows - gap_thickness:
            tear_image[gap_position:gap_position+gap_thickness, :] = gap_color

    return tear_image

def main():
#    global apply_distortion, next_distortion_time
    distortion_mode_enabled = False  # toggled with 'D' key
    apply_distortion = False         # whether a distortion is currently being applied
    distortion_duration = 1.0        # how long a distortion lasts
    next_distortion_time = time.time() + random.uniform(5, 15)
    apply_distortion_until = 0
    distortion_start_time = 0

    if not glfw.init():
        print("Could not initialize GLFW")
        return

    width, height = 1024, 768
    window = glfw.create_window(width, height, "OpenCV + OpenGL + GLFW", None, None)
    if not window:
        glfw.terminate()
        print("Could not create GLFW window")
        return

    glfw.make_context_current(window)

    textureid = asimov.util.create_texture()
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(-1, 1, -1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW)

    # OpenCV Video Capture
    vct = VideoCaptureThread(0, width, height)

    # Start Flask in a separate thread
    ft = FlaskThread(vct)

    while not glfw.window_should_close(window):
        frame = vct.get_frame() # ret, frame = cap.read()
        if frame is None:
#            time.sleep(0.1)
            continue
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Toggle distortion randomly
#        if time.time() >= next_distortion_time:
#            apply_distortion = not apply_distortion
#            next_distortion_time = time.time() + random.uniform(2, 5)
        
        frame = processframe(frame)


        frame = cv2.flip(frame, 0)

        update_texture(textureid, frame)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        asimov.util.render_quad(textureid)

        glfw.swap_buffers(window)
        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break
        elif glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
            distortion_mode_enabled = not distortion_mode_enabled
            print(f"{distortion_mode_enabled=}")
            time.sleep(0.2) # debounce

        current_time = time.time()
        if distortion_mode_enabled:
            if not apply_distortion_flag and current_time >= next_distortion_time:
                # Start distortion
                apply_distortion_flag = True
                distortion_start_time = current_time
                distortion_duration = random.uniform(0.5, 1.5)
                distortion_index = random.randint(0, 3)  # pick once
#                apply_distortion(shader_program, distortion_index)  # <-- your function
                print(f"Starting distortion {distortion_index}")
            elif apply_distortion_flag and current_time >= distortion_start_time + distortion_duration:
                # End distortion
                apply_distortion_flag = False
#                apply_distortion(shader_program, -1)  # disable all effects
                next_distortion_time = current_time + random.uniform(5, 15)
                print("Distortion ended")

    # Cleanup
#    cap.release()
    vct.stop()
    ft.stop()
    glfw.destroy_window(window)
    glfw.terminate()

if __name__ == '__main__':
    main()
