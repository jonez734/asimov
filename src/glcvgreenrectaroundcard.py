import time

import cv2

import numpy as np

import glfw

import OpenGL.GL as gl
import OpenGL.GLU as glu
import OpenGL.GLUT as glut  # For text rendering

# Window dimensions
width, height = 640, 480
texture_id = None

rect_buffer = []
DISPLAY_TIME = 2.0

def detect_cards(frame):
    """Detect playing cards and store rectangles with timestamps"""
    global rect_buffer
    new_rectangles = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    current_time = time.time()

    for cnt in contours:
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(cnt)
            if cv2.contourArea(cnt) > 1000:
                new_rectangles.append((x, y, w, h, current_time))
    # Add new rectangles to the buffer
    rect_buffer.extend(new_rectangles)

    # Remove old rectangles
    rect_buffer = [(x, y, w, h, t) for (x, y, w, h, t) in rect_buffer if current_time - t < DISPLAY_TIME]

    return rect_buffer  # Return the updated list

def create_texture():
    """Create an OpenGL texture for the webcam feed."""
    global texture_id
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

def update_texture(frame):
    """Update the OpenGL texture with the latest camera frame."""
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, frame.shape[1], frame.shape[0], 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, frame_rgb)

def draw_texture():
    """Render the video frame as a textured quad."""
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    
    gl.glBegin(gl.GL_QUADS)
    gl.glTexCoord2f(0, 1); gl.glVertex2f(0, 0)
    gl.glTexCoord2f(1, 1); gl.glVertex2f(width, 0)
    gl.glTexCoord2f(1, 0); gl.glVertex2f(width, height)
    gl.glTexCoord2f(0, 0); gl.glVertex2f(0, height)
    gl.glEnd()
    
    gl.glDisable(gl.GL_TEXTURE_2D)

def draw_rectangle(x, y, w, h):
    """Draw an outlined rectangle using OpenGL."""
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(x, height - y)
    gl.glVertex2f(x + w, height - y)
    gl.glVertex2f(x + w, height - (y + h))
    gl.glVertex2f(x, height - (y + h))
    gl.glEnd()

def draw_text(x, y, text):
    """Render text using GLUT."""
    gl.glRasterPos2f(x, height - y)
    for ch in text:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_18, ord(ch))

def render_scene(frame, rectangles):
    """Render the video frame and detected rectangles using OpenGL."""
    gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
    gl.glLoadIdentity()
    
    # Fix OpenGL Projection
    gl.glViewport(0, 0, width, height)
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    glu.gluOrtho2D(0, width, 0, height)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    # Update the OpenGL texture with the latest frame
    update_texture(frame)

    # Draw the webcam frame
    draw_texture()

    # Draw detected rectangles
    gl.glColor4f(0, 0.5, 0, 0.5)  # Black for rectangles & text
    for x, y, w, h, _ in rect_buffer:
        draw_rectangle(x, y, w, h)
        draw_text(x + 5, y - 15, f"Area: {w*h}")
    gl.glColor4f(1.0, 1.0, 1.0, 1.0)

    glfw.swap_buffers(window)  # Swap front and back buffers

def key_callback(window, key, scancode, action, mods):
    """Handle key events."""
    if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
        glfw.set_window_should_close(window, True)

def main():
    global window

    # Initialize GLFW
    if not glfw.init():
        return

    # Initialize GLUT (needed for text)
    glut.glutInit()

    # Create a GLFW window
    window = glfw.create_window(width, height, "OpenGL Card Detection", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glfw.set_key_callback(window, key_callback)  # Handle ESC key
    gl.glClearColor(1, 1, 1, 1)

    create_texture()

    # transparency
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    cap = cv2.VideoCapture(0)  # Webcam

    while not glfw.window_should_close(window):
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        rectangles = detect_cards(frame)
        render_scene(frame, rectangles)
        glfw.poll_events()

    cap.release()
    glfw.destroy_window(window)
    glfw.terminate()

if __name__ == "__main__":
    main()
