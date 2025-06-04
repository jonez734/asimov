from OpenGL.GL import *
from OpenGL.GLUT import *

import cv2

# @since 20250326
def render_text(text, x, y, font=GLUT_BITMAP_8_BY_13, 
                color=(0.0, 1.0, 0.0, 1.0), 
                shadow_color=(0.0, 0.0, 0.0, 0.5), 
                offsets=None):
    """
    Render bitmap text at a specific position with optional shadow effect.

    Parameters:
        text (str): The text to render.
        x (float): X position in normalized OpenGL coordinates.
        y (float): Y position in normalized OpenGL coordinates.
        font: GLUT font (default: GLUT_BITMAP_8_BY_13).
        color (tuple): RGBA color for the text (default: Green).
        shadow_color (tuple): RGBA color for the shadow (default: Black with 50% opacity).
        offsets (list of tuples): List of (x_offset, y_offset) for shadow rendering.
    """
    if offsets is None:
        offsets = [(-0.005, 0), (0.005, 0), (0, -0.005), (0, 0.005)]  # Default shadow offsets

    def _render(text, x, y, font):
        glRasterPos2f(x, y)
        for char in text:
            glutBitmapCharacter(font, ord(char))

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Render shadow first (if applicable)
    if shadow_color:
        glColor4f(*shadow_color)
        for offset_x, offset_y in offsets:
            _render(text, x + offset_x, y + offset_y, font)

    # Render main text
    glColor4f(*color)
    _render(text, x, y, font)

    glDisable(GL_BLEND)  # Restore state

def render_quad(texture_id):
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

#def render_quad(texture_id, vertices):
#    glEnable(GL_TEXTURE_2D)
#    glBindTexture(GL_TEXTURE_2D, texture_id)
#    glBegin(GL_QUADS)
#    glTexCoord2f(0, 0)
#    glVertex2f(vertices[0][0], vertices[0][1])
#    glTexCoord2f(1, 0)
#    glVertex2f(vertices[1][0], vertices[1][1])
#    glTexCoord2f(1, 1)
#    glVertex2f(vertices[2][0], vertices[2][1])
#    glTexCoord2f(0, 1)
#    glVertex2f(vertices[3][0], vertices[3][1])
#    glEnd()
#    glDisable(GL_TEXTURE_2D)

def create_texture():
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glBindTexture(GL_TEXTURE_2D, 0)
    return texture_id

def update_texture(texture_id, frame):
    """Upload a BGR frame (e.g. from OpenCV) as a GL texture."""
    if frame is None:
        return

    # Convert BGR (OpenCV) to RGB (OpenGL expects RGB)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, _ = frame_rgb.shape

    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, frame_rgb)
    glBindTexture(GL_TEXTURE_2D, 0)
