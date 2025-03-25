import cv2
import numpy as np
import random
import time
from OpenGL.GL import *
import glfw

# Global variables
texture_id = None
apply_filter = False
next_filter_time = time.time() + random.uniform(2, 5)

# OpenCV video capture
cap = cv2.VideoCapture(0)

def create_texture():
    global texture_id
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBindTexture(GL_TEXTURE_2D, 0)

def update_texture(image):
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.shape[1], image.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, image)
    glBindTexture(GL_TEXTURE_2D, 0)

def apply_random_filter(image):
    choice = random.choice(['desaturate', 'oversaturate', 'color_shift', 'contrast'])
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
    return image

def render_quad():
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
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

def main():
    global apply_filter, next_filter_time

    if not glfw.init():
        print("Could not initialize GLFW")
        return

    window = glfw.create_window(640, 480, "OpenCV + OpenGL + GLFW", None, None)
    if not window:
        glfw.terminate()
        print("Could not create GLFW window")
        return

    glfw.make_context_current(window)

    create_texture()
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(-1, 1, -1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW)

    while not glfw.window_should_close(window):
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Toggle filter randomly
        if time.time() >= next_filter_time:
            apply_filter = not apply_filter
            next_filter_time = time.time() + random.uniform(2, 5)

        if apply_filter:
            frame = apply_random_filter(frame)

        frame = cv2.flip(frame, 0)
        update_texture(frame)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        render_quad()
        glfw.swap_buffers(window)
        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break

    # Cleanup
    cap.release()
    glfw.destroy_window(window)
    glfw.terminate()

if __name__ == '__main__':
    main()
