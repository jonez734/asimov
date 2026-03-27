import cv2
import numpy as np
import random
import time

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
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glVertex2f,
)

# Global variables
texture_id = None
apply_distortion = False
next_distortion_time = time.time() + random.uniform(2, 5)

# OpenCV video capture
cap = cv2.VideoCapture(1)


def create_texture():
    global texture_id
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBindTexture(GL_TEXTURE_2D, 0)


def update_texture(image):
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGB,
        image.shape[1],
        image.shape[0],
        0,
        GL_RGB,
        GL_UNSIGNED_BYTE,
        image,
    )
    glBindTexture(GL_TEXTURE_2D, 0)


def apply_random_distortion(image):
    choice = random.choice(
        [
            "desaturate",
            "oversaturate",
            "color_shift",
            "contrast",
            "whitenoise",
            "tearing",
        ]
    )
    if choice == "desaturate":
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif choice == "oversaturate":
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        hsv[..., 1] = np.clip(hsv[..., 1] * 2.0, 0, 255)
        image = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    elif choice == "color_shift":
        b, g, r = cv2.split(image)
        image = cv2.merge([g, r, b])
    elif choice == "contrast":
        alpha = random.uniform(0.5, 1.5)
        image = cv2.convertScaleAbs(image, alpha=alpha, beta=0)
    elif choice == "whitenoise":
        intensity = random.randint(32, 128)
        noise = np.random.randint(0, intensity, image.shape, dtype="uint8")
        image = cv2.add(image, noise)
    elif choice == "tearing":
        image = tearing_effect(image)
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


def tearing_effect(image):
    rows, cols, _ = image.shape
    num_slices = random.randint(3, 8)  # number of tearing "slices"
    tear_image = image.copy()

    for _ in range(num_slices):
        y = random.randint(0, rows - 20)
        h = random.randint(5, 20)  # height of tear band
        shift = random.randint(-30, 30)  # how much to horizontally offset

        # Shift the band horizontally
        tear_image[y : y + h, :] = np.roll(tear_image[y : y + h, :], shift, axis=1)

        # Add a thin black line above or below to simulate a gap
        gap_position = y + h if (y + h) < rows else y - 1
        gap_thickness = random.randint(1, 3)
        gap_color = random.randint(0, 30)  # very dark gray instead of pure black
        if 0 <= gap_position < rows - gap_thickness:
            tear_image[gap_position : gap_position + gap_thickness, :] = gap_color

    return tear_image


def main():
    global apply_distortion, next_distortion_time

    if not glfw.init():
        print("Could not initialize GLFW")
        return

    window = glfw.create_window(800, 600, "OpenCV + OpenGL + GLFW", None, None)
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

        # Toggle distortion randomly
        #        if time.time() >= next_distortion_time:
        #            apply_distortion = not apply_distortion
        #            next_distortion_time = time.time() + random.uniform(2, 5)

        if apply_distortion:
            frame = apply_random_distortion(frame)

        frame = cv2.flip(frame, 0)
        update_texture(frame)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        render_quad()
        glfw.swap_buffers(window)
        glfw.poll_events()

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break
        elif glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
            apply_distortion = not apply_distortion
            print(f"{apply_distortion=}")
            time.sleep(0.2)  # debounce

    # Cleanup
    cap.release()
    glfw.destroy_window(window)
    glfw.terminate()


if __name__ == "__main__":
    main()
