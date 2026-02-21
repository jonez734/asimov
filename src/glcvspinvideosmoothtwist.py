import cv2
import numpy as np
import glfw
import OpenGL.GL as gl
import OpenGL.GL.shaders as shaders
import random
import math
from typing import Any

from asimov.util import (
    create_texture,
    update_texture,
    render_quad,
    lerp,
    smooth_step,
    stable_phase,
)

# Initialize OpenCV video capture
video_path = 1
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video file.")
    exit(1)

# Initialize GLFW
if not glfw.init():
    print("Error: Could not initialize GLFW.")
    exit(1)

# Create OpenGL window
window = glfw.create_window(800, 600, "OpenGL Video Player", None, None)
if not window:
    glfw.terminate()
    exit(1)

glfw.make_context_current(window)

# Compile OpenGL shaders
vertex_shader = """
#version 330 core
layout (location = 0) in vec3 position;
layout (location = 1) in vec2 texCoords;
out vec2 TexCoords;
void main() {
    TexCoords = texCoords;
    gl_Position = vec4(position, 1.0);
}
"""

fragment_shader = """
#version 330 core
out vec4 FragColor;
in vec2 TexCoords;
uniform sampler2D videoTexture;
void main() {
    FragColor = texture(videoTexture, TexCoords);
}
"""

shader = shaders.compileProgram(
    shaders.compileShader(vertex_shader, gl.GL_VERTEX_SHADER),
    shaders.compileShader(fragment_shader, gl.GL_FRAGMENT_SHADER)
)

# Create VAO and VBO
VAO = gl.glGenVertexArrays(1)
VBO = gl.glGenBuffers(1)
EBO = gl.glGenBuffers(1)

gl.glBindVertexArray(VAO)
gl.glBindBuffer(gl.GL_ARRAY_BUFFER, VBO)
gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, EBO)

# Index buffer (constant)
indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)
gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)

# Enable vertex attributes
gl.glEnableVertexAttribArray(0)
gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 5 * 4, gl.ctypes.c_void_p(0))

gl.glEnableVertexAttribArray(1)
gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_FALSE, 5 * 4, gl.ctypes.c_void_p(3 * 4))

gl.glBindVertexArray(0)

# Create Texture using asimov.util
texture = create_texture()

# Animation state using stable_phase for unique random seeds
class SmoothTarget:
    def __init__(self, seed: Any, x_range=(-0.5, 0.5), y_range=(-0.5, 0.5), z_range=(-0.5, 0.0), angle_range=(-15, 15)):
        self.seed = seed
        self.x_range = x_range
        self.y_range = y_range
        self.z_range = z_range
        self.angle_range = angle_range
        self.current = self._random_target()
        self.target = self._random_target()
        self.progress = 1.0
    
    def _random_target(self):
        return {
            'x': random.uniform(*self.x_range),
            'y': random.uniform(*self.y_range),
            'z': random.uniform(*self.z_range),
            'angle': random.uniform(*self.angle_range),
        }
    
    def update(self, dt: float = 1/60) -> dict:
        """Update and return interpolated values."""
        self.progress += dt
        t = smooth_step(min(self.progress, 1.0))
        
        if self.progress >= 1.0:
            self.current = self.target
            self.target = self._random_target()
            self.progress = 0.0
        
        return {
            'x': lerp(self.current['x'], self.target['x'], t),
            'y': lerp(self.current['y'], self.target['y'], t),
            'z': lerp(self.current['z'], self.target['z'], t),
            'angle': lerp(self.current['angle'], self.target['angle'], t),
        }

# Initialize animation
anim = SmoothTarget("video_player")

# Main loop
while not glfw.window_should_close(window):
    # Check for ESC key
    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        break

    # Read a frame from the video
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret:
            break

    # Convert frame to OpenGL texture format
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.flip(frame, axis=0)

    # Update texture using asimov.util
    update_texture(texture, frame)

    # Get interpolated animation values
    anim_state = anim.update()

    # Smooth rotation interpolation
    theta = math.radians(anim_state['angle'])
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    def rotate_vertex(x, y):
        return (
            x * cos_theta - y * sin_theta,
            x * sin_theta + y * cos_theta
        )

    # Rotated quad vertices
    v0 = rotate_vertex(-0.5, -0.5)
    v1 = rotate_vertex( 0.5, -0.5)
    v2 = rotate_vertex( 0.5,  0.5)
    v3 = rotate_vertex(-0.5,  0.5)

    vertices = np.array([
        v0[0] + anim_state['x'], v0[1] + anim_state['y'], anim_state['z'],  0.0, 0.0,
        v1[0] + anim_state['x'], v1[1] + anim_state['y'], anim_state['z'],  1.0, 0.0,
        v2[0] + anim_state['x'], v2[1] + anim_state['y'], anim_state['z'],  1.0, 1.0,
        v3[0] + anim_state['x'], v3[1] + anim_state['y'], anim_state['z'],  0.0, 1.0
    ], dtype=np.float32)

    # Update VBO with new vertex data
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, VBO)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_DYNAMIC_DRAW)

    # Clear screen and render quad
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    gl.glUseProgram(shader)
    gl.glBindVertexArray(VAO)
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)

    # Swap buffers and poll events
    glfw.swap_buffers(window)
    glfw.poll_events()

# Cleanup
cap.release()
glfw.terminate()
