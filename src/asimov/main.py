import random
import time
import threading

import cv2
import numpy as np

from OpenGL.GL import *

from flask import Flask, Response

import glfw

from cvzone.HandTrackingModule import HandDetector

import asimov.util, asimov.distort

# Global variables
#texture_id = None
#next_distortion_time = time.time() + random.uniform(2, 5)

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
        self.app.add_url_rule('/video', 'video_feed', self.video_feed)

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

# moved to asimov.util
#def update_texture(textureid, image):
#    glBindTexture(GL_TEXTURE_2D, textureid)
#    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.shape[1], image.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, image)
#    glBindTexture(GL_TEXTURE_2D, 0)

def key_callback(window, key, scancode, action, mods):
    global distortions_enabled
    if key == glfw.KEY_D and action == glfw.PRESS:
        distortions_enabled = not distortions_enabled
        print(f"Distortions {'enabled' if distortions_enabled else 'disabled'}")

def apply_texture_distortion(frame):
    if not hasattr(apply_texture_distortion, "active"):
        apply_texture_distortion.active = False
        apply_texture_distortion.start_time = 0
        apply_texture_distortion.duration = 1.5
        apply_texture_distortion.next_time = time.time() + random.uniform(5, 10)
        apply_texture_distortion.effect_name = None

    current_time = time.time()

    if apply_texture_distortion.active:
        if current_time - apply_texture_distortion.start_time > apply_texture_distortion.duration:
            apply_texture_distortion.active = False
            apply_texture_distortion.next_time = current_time + random.uniform(4, 8)
            apply_texture_distortion.effect_name = None
            return frame

        distorted = np.copy(frame)
        t = current_time

        effect = apply_texture_distortion.effect_name

        if effect == 'desaturate':
            distorted = cv2.cvtColor(distorted, cv2.COLOR_RGB2GRAY)
            distorted = cv2.cvtColor(distorted, cv2.COLOR_GRAY2RGB)
        elif effect == 'oversaturate':
            hsv = cv2.cvtColor(distorted, cv2.COLOR_RGB2HSV)
            hsv[..., 1] = np.clip(hsv[..., 1] * 2.0, 0, 255)
            distorted = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        elif effect == 'color_shift':
            b, g, r = cv2.split(distorted)
            distorted = cv2.merge([g, r, b])
        elif effect == 'contrast':
            alpha = random.uniform(0.5, 1.5)
            distorted = cv2.convertScaleAbs(distorted, alpha=alpha, beta=0)
        elif effect == 'whitenoise':
            intensity = random.randint(32, 128)
            noise = np.random.randint(0, intensity, distorted.shape, dtype='uint8')
            distorted = cv2.add(distorted, noise)
        elif effect == 'tearing':
            distorted = tearing_effect(distorted)

        elif effect == "horizontal_wave":
            height, width = distorted.shape[:2]
            distorted_float = distorted.astype(np.float32)
            amplitude = 20
            frequency = 20
            phase = t * 5
            y_indices_float = np.arange(height)[:, np.newaxis] / frequency
            x_offsets_float = amplitude * np.sin(y_indices_float + phase)
            shifted_frame = np.zeros_like(distorted_float)
            for y in range(height):
                offset_float = x_offsets_float[y, 0]
                offset_int = int(offset_float)

                for x in range(width):
                    src_x = int(np.round(np.clip(x - offset_float, 0, width - 1)))
                    shifted_frame[y, x] = distorted_float[y, src_x]
            distorted = shifted_frame.astype(np.uint8)
        elif effect == "vertical_wave":
            height, width = distorted.shape[:2]
            distorted_float = distorted.astype(np.float32)
            amplitude = 20
            frequency = 20
            phase = t * 5
            y_indices = np.arange(height)[:, np.newaxis]  # Shape (height, 1)
            x_offsets = amplitude * np.sin(y_indices / frequency + phase)  # Shape (height, 1)
            shifted_frame = np.zeros_like(distorted_float)
            for y in range(height):
                offset = int(x_offsets[y, 0])  # Get the offset for the current row
                shifted_x = np.clip(np.arange(width) + offset, 0, width - 1)
                shifted_frame[y, :] = distorted_float[y, shifted_x]
            distorted = shifted_frame.astype(np.uint8)
        elif effect == "diagonal_wave":
            height, width = distorted.shape[:2]
            distorted_float = distorted.astype(np.float32)
            amplitude = 15
            frequency = 15
            phase = t * 5
            row_indices, col_indices = np.indices((height, width)).astype(np.float32)
            offset = amplitude * np.sin((row_indices + col_indices) / frequency + phase)
            shifted_frame = np.zeros_like(distorted_float)
            for i in range(height):
                for j in range(width):
                    offset_val = int(offset[i, j])
                    new_row = np.clip(i + offset_val, 0, height - 1)
                    new_col = np.clip(j + offset_val, 0, width - 1)
                    shifted_frame[new_row, new_col] = distorted_float[i, j] # Note the assignment
            distorted = shifted_frame.astype(np.uint8)
        elif effect == "rgb_split":
            offset = 0.01 * np.sin(t * 20)
            distorted[:, 0] += offset
        elif effect == "geometry_noise":
            noise = (np.random.rand(*distorted.shape) - 0.5) * 0.005
            distorted += noise
        elif effect == "tear":
            row = random.randint(0, distorted.shape[0] - 1)
            offset = (random.random() - 0.5) * 0.05
            distorted[row:, 0] += offset
        elif effect == "texture_whitenoise":
            height, width = frame.shape[:2]
            channels = frame.shape[2] if len(frame.shape) == 3 else 1
            random_noise = np.random.randint(0, 256, size=(height, width, channels), dtype=np.uint8)
            alpha = 0.2 + 0.1 * np.sin(current_time * 5)  # Vary alpha over time
            alpha = np.clip(alpha, 0.1, 0.3)  # Keep alpha within a reasonable range
            frame = cv2.addWeighted(frame, 1 - alpha, random_noise, alpha, 0)
        return distorted
    else:
        if current_time >= apply_texture_distortion.next_time:
            apply_texture_distortion.active = True
            apply_texture_distortion.start_time = current_time
            apply_texture_distortion.duration = random.uniform(1.5, 3.0)

            effect_list = [
#                "tearing",
#                "contrast",
                "color_shift",
#                "whitenoise",
#                "horizontal_wave",
#                "vertical_wave",
#                "diagonal_wave",
#                "rgb_split",
#                "noise",
#                "tear",
#                "texture_whitenoise"
            ]

            apply_texture_distortion.effect_name = random.choice(effect_list)
            print(f"Starting distortion: {apply_texture_distortion.effect_name}")
            if apply_texture_distortion.effect_name == "texture_whitenoise":
                apply_texture_distortion.white_noise_texture = None # Generate new noise each time

    return frame

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

def main():
    distortion_mode_enabled = False  # toggled with 'D' key
##    apply_distortion = False         # whether a distortion is currently being applied
##    distortion_duration = 1.0        # how long a distortion lasts
##    next_distortion_time = time.time() + random.uniform(5, 15)
##    apply_distortion_until = 0

    original_vertices = np.array([
        [-1.0, -1.0],
        [ 1.0, -1.0],
        [ 1.0,  1.0],
        [-1.0,  1.0]
    ], dtype=np.float32)

    # Corresponding texture coordinates (same order)
    tex_coords = np.array([
        [0.0, 1.0],
        [1.0, 1.0],
        [1.0, 0.0],
        [0.0, 0.0]
    ], dtype=np.float32)

    if not glfw.init():
        print("Could not initialize GLFW")
        raise RuntimeError("could not initialize GLFW")


    width, height = (1024, 768)
    window = glfw.create_window(width, height, "Project Asimov", None, None)
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

    last_toggle_time = 0
    apply_texture_distortion = asimov.distort.WhiteNoise()

    while not glfw.window_should_close(window):
        frame = vct.get_frame() # ret, frame = cap.read()
        if frame is None:
            continue

        frame = processframe(frame)

        frame = cv2.flip(frame, 0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        processed_frame = frame
        current_time = time.time()

        if distortion_mode_enabled:
            # Only call distortion if it's active or due to start
            if apply_texture_distortion.active or current_time >= apply_texture_distortion.next_time:
                processed_frame = apply_texture_distortion(processed_frame)

        asimov.util.update_texture(textureid, processed_frame)
        asimov.util.render_quad(textureid)
        glfw.swap_buffers(window)
        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break
        elif glfw.get_key(window, glfw.KEY_D) == glfw.PRESS and time.time() - last_toggle_time > 0.2:
            distortion_mode_enabled = not distortion_mode_enabled
            print(f"{distortion_mode_enabled=}")
            last_toggle_time = time.time()

    # Cleanup
    vct.stop()
    ft.stop()
    glfw.destroy_window(window)
    glfw.terminate()

if __name__ == '__main__':
    main()
