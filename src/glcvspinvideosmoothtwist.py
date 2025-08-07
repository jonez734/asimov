import cv2
import numpy as np
import glfw
import OpenGL.GL as gl
import OpenGL.GL.shaders as shaders
import random
import math

# Initialize OpenCV video capture
video_path = 0 # "video.mp4"  # Change to your video file
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

# Create Texture
texture = gl.glGenTextures(1)
gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

# LERP function for smooth interpolation
def lerp(start, end, t):
    return start + t * (end - start)

# Initial and target positions
current_x = current_y = current_z = 0.0
target_x = random.uniform(-0.5, 0.5)
target_y = random.uniform(-0.5, 0.5)
target_z = random.uniform(-0.5, 0.0)

# Rotation parameters
current_angle = 0.0
target_angle = random.uniform(-15, 15)  # Rotate up to ±15 degrees
frames_to_change = 60  # Change position & rotation every 60 frames (~1 sec at 60 FPS)
frame_counter = 0

# Main loop
while not glfw.window_should_close(window):
    # Check for ESC key
    if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
        break

    # Read a frame from the video
    ret, frame = cap.read()
    if not ret:
        break  # End of video

    # Convert frame to OpenGL texture format
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.flip(frame, axis=0)  # Flip vertically for OpenGL

    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, frame.shape[1], frame.shape[0], 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, frame)

    # Smooth position interpolation
    t = frame_counter / frames_to_change
    smoothed_x = lerp(current_x, target_x, t)
    smoothed_y = lerp(current_y, target_y, t)
    smoothed_z = lerp(current_z, target_z, t)

    # Smooth rotation interpolation
    smoothed_angle = lerp(current_angle, target_angle, t)
    theta = math.radians(smoothed_angle)

    # Generate new target after frames_to_change frames
    if frame_counter >= frames_to_change:
        current_x, current_y, current_z = target_x, target_y, target_z
        current_angle = target_angle
        target_x = random.uniform(-0.5, 0.5)
        target_y = random.uniform(-0.5, 0.5)
        target_z = random.uniform(-0.5, 0.0)
        target_angle = random.uniform(-15, 15)  # New random rotation
        frame_counter = 0

    frame_counter += 1

    # Rotation matrix for 2D rotation
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
        v0[0] + smoothed_x, v0[1] + smoothed_y, smoothed_z,  0.0, 0.0,  # Bottom-left
        v1[0] + smoothed_x, v1[1] + smoothed_y, smoothed_z,  1.0, 0.0,  # Bottom-right
        v2[0] + smoothed_x, v2[1] + smoothed_y, smoothed_z,  1.0, 1.0,  # Top-right
        v3[0] + smoothed_x, v3[1] + smoothed_y, smoothed_z,  0.0, 1.0   # Top-left
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
