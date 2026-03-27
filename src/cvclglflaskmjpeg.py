import time
import threading

import cv2
from flask import Flask, Response
import glfw

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_LINEAR,
    GL_MODELVIEW,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGB,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glClear,
    glColor3f,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glLoadIdentity,
    glMatrixMode,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glTranslatef,
    glVertex2f,
    glViewport,
)
from OpenGL.GLUT import glutInit
from OpenGL.GLU import gluOrtho2D

from asimov.util import render_text


def create_texture():
    """Create an OpenGL texture"""
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return texture


def update_texture(texture, frame):
    """Update OpenGL texture with a new frame"""
    glBindTexture(GL_TEXTURE_2D, texture)
    frame = cv2.flip(frame, 0)  # OpenGL and OpenCV have inverted y-axes
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGB,
        frame.shape[1],
        frame.shape[0],
        0,
        GL_RGB,
        GL_UNSIGNED_BYTE,
        frame,
    )


def render_quad(texture):
    """Render a textured rectangle with the OpenGL texture"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -1.0)

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(-1, -1)
    glTexCoord2f(1, 0)
    glVertex2f(1, -1)
    glTexCoord2f(1, 1)
    glVertex2f(1, 1)
    glTexCoord2f(0, 1)
    glVertex2f(-1, 1)
    glEnd()

    glDisable(GL_TEXTURE_2D)


# def capture_frame(width, height):
#    """Capture OpenGL framebuffer and return as an OpenCV image"""
#    glReadBuffer(GL_FRONT)
#    pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
#    image = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 3)
#    return cv2.flip(image, 0)  # Flip back for OpenCV

# def generate_frames(video_thread):
#    while True:
#        frame = video_thread.get_frame() # success, frame = cap.read()
#        if frame is None:
#            continue
#
#        # Optional: Process frame with OpenGL (You can integrate PyOpenGL here)
#
#        ret, buffer = cv2.imencode('.jpg', frame)
#        if not ret:
#            continue
#        yield (b'--frame\r\n'
#               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# @app.route('/video-feed')
# def video_feed():
#    return Response(generate_frames(vct), mimetype='multipart/x-mixed-replace; boundary=frame')


class VideoCaptureThread(threading.Thread):
    def __init__(self, src=0, width=640, height=480):
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
            #            if self.frame is None:
            #                return None
            #            _, buffer = cv2.imencode('.jpg', self.frame)
            #            return buffer.tobytes()
            return self.frame

    #    def read(self):
    #        with self.lock:
    #            return self.frame

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
        self.app.add_url_rule("/video_feed", "video_feed", self.video_feed)

    def run(self):
        self.app.run(
            host="0.0.0.0", port=5000, threaded=True, debug=True, use_reloader=False
        )

    def generate_frames(self):
        while self.running:
            frame = self.vct.get_frame()  # success, frame = cap.read()
            if frame is None:
                continue

            # Optional: Process frame with OpenGL (You can integrate PyOpenGL here)

            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )

    def video_feed(self):
        return Response(
            self.generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )

    def stop(self):
        self.running = False


#        self.thread.join()


def initgl(width=640, height=480):
    # Initialize GLUT before creating window
    glutInit()

    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(-1, 1, -1, 1)
    # gluOrtho2D(0, width, 0, height)
    glMatrixMode(GL_MODELVIEW)


def main():
    if not glfw.init():
        return

    width, height = 1024, 768  # 640, 480
    window = glfw.create_window(width, height, "asimov | 20250210)", None, None)
    glfw.make_context_current(window)

    initgl(width, height)

    # Create OpenGL texture
    texture = create_texture()

    # OpenCV Video Capture
    vct = VideoCaptureThread(1, width, height)  # cv2.CAP_V4L2)

    # Start Flask in a separate thread
    ft = FlaskThread(vct)

    frame_count = 0
    start_time = time.time()
    fps = 0

    while not glfw.window_should_close(window):
        glfw.poll_events()

        # Measure FPS every second
        frame_count += 1
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time >= 1.0:  # Update FPS every second
            fps = frame_count / elapsed_time
            frame_count = 0
            start_time = current_time

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break  # Exit the loop if Escape key is pressed

        frame_start = time.time()
        frame = vct.get_frame()
        if frame is None:
            continue
        frame_end = time.time()

        gl_start = time.time()
        glClear(GL_COLOR_BUFFER_BIT)

        glColor3f(1.0, 1.0, 1.0)  # White color for the video

        update_texture(texture, frame)
        render_quad(texture)

        gl_end = time.time()

        norm_x = (2 * 20 / width) - 1
        norm_y = 1 - (2 * 20 / height)
        render_text(
            f"cv: {(frame_end - frame_start) * 1000:.2f} gl: {(gl_end - gl_start) * 1000:.2f} FPS: {fps:3.2f}",
            norm_x,
            norm_y,
        )
        print(f"{fps=}")

        glfw.swap_buffers(window)

        # Capture frame from OpenGL and send to GStreamer
    #        opengl_frame = capture_frame(width, height)
    #       send_to_gstreamer(opengl_frame)

    vct.stop()
    ft.stop()
    #    pipeline.set_state(Gst.State.NULL)
    glfw.terminate()


#    flask_thread = threading.Thread(target=run_flask, daemon=True)
#    flask_thread.start()

if __name__ == "__main__":
    main()
