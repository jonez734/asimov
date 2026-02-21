import cv2
import numpy as np
import glfw
import OpenGL.GL as gl
import OpenGL.GL.shaders as shaders
import random
import math

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

# Animation state - moves until hitting border, then changes direction
anim_state = {
    'x': 0.0,
    'y': 0.0,
    'z': 0.0,
    'angle': 0.0,
    'vel_x': 0.01,
    'vel_y': 0.01,
    'vel_z': 0.0,
    'vel_angle': 0.2,
    'x_range': (-0.8, 0.8),
    'y_range': (-0.8, 0.8),
    'z_range': (-0.3, 0.0),
    'angle_range': (-15, 15),
}

QUAD_SIZE = 0.5  # Half-size (center to edge)

def anim_update(state):
    # Quad edges accounting for quad size
    effective_x_min = state['x_range'][0] + QUAD_SIZE
    effective_x_max = state['x_range'][1] - QUAD_SIZE
    effective_y_min = state['y_range'][0] + QUAD_SIZE
    effective_y_max = state['y_range'][1] - QUAD_SIZE
    
    # Check bounds and reverse velocity BEFORE moving past border
    next_x = state['x'] + state['vel_x']
    next_y = state['y'] + state['vel_y']
    next_angle = state['angle'] + state['vel_angle']
    
    if next_x <= effective_x_min or next_x >= effective_x_max:
        state['vel_x'] *= -1
    
    if next_y <= effective_y_min or next_y >= effective_y_max:
        state['vel_y'] *= -1
    
    if next_angle <= state['angle_range'][0] or next_angle >= state['angle_range'][1]:
        state['vel_angle'] *= -1
    
    # Update positions
    state['x'] += state['vel_x']
    state['y'] += state['vel_y']
    state['z'] += state['vel_z']
    state['angle'] += state['vel_angle']
    
    return state

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

    # Flip vertically for OpenGL texture coordinates
    frame = np.flip(frame, axis=0)

    # Update texture using asimov.util (handles BGR->RGB conversion)
    update_texture(texture, frame)

    # Get interpolated animation values
    anim_vals = anim_update(anim_state)

    # Smooth rotation interpolation
    theta = math.radians(anim_vals['angle'])
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
        v0[0] + anim_vals['x'], v0[1] + anim_vals['y'], anim_vals['z'],  0.0, 0.0,
        v1[0] + anim_vals['x'], v1[1] + anim_vals['y'], anim_vals['z'],  1.0, 0.0,
        v2[0] + anim_vals['x'], v2[1] + anim_vals['y'], anim_vals['z'],  1.0, 1.0,
        v3[0] + anim_vals['x'], v3[1] + anim_vals['y'], anim_vals['z'],  0.0, 1.0
    ], dtype=np.float32)

    # Update VBO with new vertex data
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, VBO)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_DYNAMIC_DRAW)

    # Clear screen and render quad
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    gl.glUseProgram(shader)
    
    # Bind texture for shader
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    loc = gl.glGetUniformLocation(shader, "videoTexture")
    if loc >= 0:
        gl.glUniform1i(loc, 0)
    
    gl.glBindVertexArray(VAO)
    gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)

    # Swap buffers and poll events
    glfw.swap_buffers(window)
    glfw.poll_events()

# Cleanup
cap.release()
glfw.terminate()
