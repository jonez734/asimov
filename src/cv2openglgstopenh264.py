import time

import cv2
import glfw
import numpy as np
import gi
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

from asimov.util import render_text

gi.require_version("Gst", "1.0")
from gi.repository import Gst

# Initialize GStreamer
Gst.init(None)

#gst_pipeline = ("appsrc name=src format=time ! videoconvert ! video/x-raw,format=I420, width=640, height=480, framerate=30/1 ! "
#    "openh264enc bitrate=500000 ! rtph264pay ! "
#    "udpsink host=127.0.0.1 port=5000")
gst_pipeline = ("appsrc name=src format=time is-live=true ! videoconvert ! autovideosink")



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
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, frame.shape[1], frame.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, frame)


def render_quad(texture):
    """Render a textured rectangle with the OpenGL texture"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -1.0)

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)

    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(-1, -1)
    glTexCoord2f(1, 0); glVertex2f(1, -1)
    glTexCoord2f(1, 1); glVertex2f(1, 1)
    glTexCoord2f(0, 1); glVertex2f(-1, 1)
    glEnd()

    glDisable(GL_TEXTURE_2D)


def capture_frame(width, height):
    """Capture OpenGL framebuffer and return as an OpenCV image"""
    glReadBuffer(GL_FRONT)
    pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
    image = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 3)
    return cv2.flip(image, 0)  # Flip back for OpenCV


def send_to_gstreamer(frame):
    """Send OpenCV image to GStreamer pipeline"""
    height, width, _ = frame.shape
    data = frame.tobytes()

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)

    # Create a GStreamer buffer
    buf = Gst.Buffer.new_allocate(None, len(data), None)
    buf.fill(0, data)

#?    buf.pts = buf.dts = Gst.util_uint64_scale(GLib.get_monotonic_time(), 1, 1000000)
    buf.pts = buf.dts = Gst.util_uint64_scale(glfw.get_time(), Gst.SECOND, 1)
    buf.duration = Gst.util_uint64_scale(1, Gst.SECOND, 30)

    # Push buffer to pipeline
    ret = appsrc.emit("push-buffer", buf)
    if ret != Gst.FlowReturn.OK:
        print("error pushing buffer: ", ret)
    return True


def main():
    """Main function to capture video from OpenCV and render it in OpenGL"""
    if not glfw.init():
        return

    width, height = 640, 480
    window = glfw.create_window(width, height, "asimov | 20250207)", None, None)
    glfw.make_context_current(window)

    # Set up GStreamer pipeline
    pipeline = Gst.parse_launch(gst_pipeline)
    appsrc = pipeline.get_by_name("src")
    appsrc.set_property("format", Gst.Format.TIME)
    appsrc.set_property("is-live", True)
    pipeline.set_state(Gst.State.PLAYING)

    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(-1, 1, -1, 1)
    # gluOrtho2D(0, width, 0, height)
    glMatrixMode(GL_MODELVIEW)

    # Create OpenGL texture
    texture = create_texture()

    # OpenCV Video Capture
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Initialize GLUT before creating window
    glutInit()

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

        ret, frame = cap.read()
        if not ret:
            break

        glClear(GL_COLOR_BUFFER_BIT)

        # Render FPS text at coordinates (10, 450)

        glColor3f(1.0, 1.0, 1.0)  # White color for the video
        update_texture(texture, frame)
        render_quad(texture)

        norm_x = (2 * 20 / width) - 1
        norm_y = 1 - (2 * 20 / height)
        render_text(f"FPS: {fps:3.2f}", norm_x, norm_y)
        print(f"{fps=}")

        glfw.swap_buffers(window)

        # Capture frame from OpenGL and send to GStreamer
        opengl_frame = capture_frame(width, height)
        send_to_gstreamer(opengl_frame)

    cap.release()
    pipeline.set_state(Gst.State.NULL)
    glfw.terminate()


if __name__ == "__main__":
    main()
