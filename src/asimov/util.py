from OpenGL.GL import *
from OpenGL.GLUT import *

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
