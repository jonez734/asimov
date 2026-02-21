import cv2
import numpy as np
import glfw
import OpenGL.GL as gl
import OpenGL.GL.shaders as shaders

from asimov.util import (
    create_texture,
    update_texture,
    rotate_vertex,
    bounce_animation_update,
    create_bounce_state,
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

# Animation state using asimov.util
anim_state = create_bounce_state()

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

    # Get animation values using asimov.util
    anim_vals = bounce_animation_update(anim_state)

    # Rotated quad vertices using asimov.util
    v0 = rotate_vertex(-0.5, -0.5, anim_vals['angle'])
    v1 = rotate_vertex( 0.5, -0.5, anim_vals['angle'])
    v2 = rotate_vertex( 0.5,  0.5, anim_vals['angle'])
    v3 = rotate_vertex(-0.5,  0.5, anim_vals['angle'])

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
