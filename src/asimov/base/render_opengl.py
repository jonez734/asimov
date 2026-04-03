# asimov/render.py

import numpy as np
import OpenGL.GL as gl
import glfw
import socket
from threading import Event

from . import conf, net

# Global variables for OpenGL resources
g_shader_program = None
g_vao = None
g_texture_id = None
g_projection_loc = None  # Location of the projection uniform in the shader

# Globals to track frame size once known
g_frame_width = None
g_frame_height = None

# Global variables for application state
current_frame = None
udp_receiver = None
stop_event = None
window = None

# --- Shader Source Code ---
# Basic Vertex Shader for a 2D textured quad
VERTEX_SHADER_SOURCE = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec2 aTexCoord;

out vec2 TexCoord;

uniform mat4 projection; // Orthographic projection matrix

void main()
{
    gl_Position = projection * vec4(aPos, 1.0);
    TexCoord = aTexCoord;
}
"""

# Basic Fragment Shader to sample a texture
FRAGMENT_SHADER_SOURCE = """
#version 330 core
out vec4 FragColor;

in vec2 TexCoord;

uniform sampler2D ourTexture; // Our texture sampler

void main()
{
    FragColor = texture(ourTexture, TexCoord);
}
"""


def _compile_shader(source, shader_type):
    """Compiles an OpenGL shader."""
    shader = gl.glCreateShader(shader_type)
    gl.glShaderSource(shader, source)
    gl.glCompileShader(shader)

    if not gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS):
        info_log = gl.glGetShaderInfoLog(shader).decode()
        raise RuntimeError(f"Shader compilation failed: {info_log}")
    return shader


def _create_shader_program(vertex_source, fragment_source):
    """Creates and links an OpenGL shader program."""
    vertex_shader = _compile_shader(vertex_source, gl.GL_VERTEX_SHADER)
    fragment_shader = _compile_shader(fragment_source, gl.GL_FRAGMENT_SHADER)

    program = gl.glCreateProgram()
    gl.glAttachShader(program, vertex_shader)
    gl.glAttachShader(program, fragment_shader)
    gl.glLinkProgram(program)

    if not gl.glGetProgramiv(program, gl.GL_LINK_STATUS):
        info_log = gl.glGetProgramInfoLog(program).decode()
        gl.glDeleteProgram(program)
        raise RuntimeError(f"Shader program linking failed: {info_log}")

    gl.glDeleteShader(vertex_shader)
    gl.glDeleteShader(fragment_shader)
    return program


def _calculate_ortho_projection(width, height):
    """Calculates an orthographic projection matrix."""
    # Ortho (left, right, bottom, top, near, far)
    # Maps screen coordinates (0,0) to (width,height) to clip space (-1 to 1)
    # Using (0, width, height, 0) to flip Y-axis for OpenCV compatibility (0,0 is top-left)
    # and match screen coordinates directly
    left, right, bottom, top, near, far = 0, width, height, 0, -1, 1

    projection = np.array(
        [
            [2.0 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2.0 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -2.0 / (far - near), -(far + near) / (far - near)],
            [0, 0, 0, 1],
        ],
        dtype=np.float32,
    ).T  # .T for column-major order expected by OpenGL

    return projection


def _framebuffer_size_callback(window, width, height):
    """Callback for window resize, updates viewport and projection."""
    gl.glViewport(0, 0, width, height)

    global g_shader_program, g_projection_loc
    if (
        g_shader_program
        and g_projection_loc is not None
        and g_frame_width
        and g_frame_height
    ):
        # Update projection to match new window size if desired,
        # but here we keep it matching the frame size (fixed)
        projection = _calculate_ortho_projection(g_frame_width, g_frame_height)
        gl.glUseProgram(g_shader_program)
        gl.glUniformMatrix4fv(g_projection_loc, 1, gl.GL_FALSE, projection)
        gl.glUseProgram(0)


def _init_opengl(width, height):
    """Initializes OpenGL for shader-based rendering."""
    global g_shader_program, g_vao, g_texture_id, g_projection_loc

    gl.glClearColor(0.0, 0.0, 0.0, 1.0)
    gl.glEnable(gl.GL_DEPTH_TEST)  # Often useful, even for 2D

    # 1. Create and Link Shader Program
    g_shader_program = _create_shader_program(
        VERTEX_SHADER_SOURCE, FRAGMENT_SHADER_SOURCE
    )
    gl.glUseProgram(g_shader_program)  # Use program once to get uniform locations

    # Get uniform location for projection matrix
    g_projection_loc = gl.glGetUniformLocation(g_shader_program, "projection")
    if g_projection_loc == -1:
        print("Warning: Could not find 'projection' uniform location.")

    # Set initial projection matrix (will update later to match actual frame size)
    projection = _calculate_ortho_projection(width, height)
    gl.glUniformMatrix4fv(g_projection_loc, 1, gl.GL_FALSE, projection)

    # Set ourTexture uniform to texture unit 0 (where we will bind our texture)
    texture_sampler_loc = gl.glGetUniformLocation(g_shader_program, "ourTexture")
    if texture_sampler_loc == -1:
        print("Warning: Could not find 'ourTexture' uniform location.")
    gl.glUniform1i(texture_sampler_loc, 0)  # Set to texture unit 0

    # 2. Setup an initial dummy VAO (will be replaced after first frame)
    g_vao = gl.glGenVertexArrays(1)
    gl.glBindVertexArray(g_vao)
    gl.glBindVertexArray(0)

    # 3. Setup Texture (parameters only, no size allocated yet)
    g_texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, g_texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)


def initialize_first_frame(frame):
    global \
        g_frame_width, \
        g_frame_height, \
        g_vao, \
        g_texture_id, \
        g_projection_loc, \
        g_shader_program

    g_frame_height, g_frame_width = frame.shape[:2]

    # 1. Update quad geometry (VAO, VBO) for this frame size
    vertices = np.array(
        [
            0.0,
            g_frame_height,
            0.0,
            0.0,
            0.0,
            g_frame_width,
            g_frame_height,
            0.0,
            1.0,
            0.0,
            g_frame_width,
            0.0,
            0.0,
            1.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ],
        dtype=np.float32,
    )

    indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

    # Delete old VAO if it exists
    if g_vao is not None:
        gl.glDeleteVertexArrays(1, [g_vao])

    g_vao = gl.glGenVertexArrays(1)
    gl.glBindVertexArray(g_vao)

    vbo = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)

    ebo = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo)
    gl.glBufferData(
        gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW
    )

    gl.glVertexAttribPointer(
        0, 3, gl.GL_FLOAT, gl.GL_FALSE, 5 * vertices.itemsize, None
    )
    gl.glEnableVertexAttribArray(0)

    gl.glVertexAttribPointer(
        1, 2, gl.GL_FLOAT, gl.GL_FALSE, 5 * vertices.itemsize, 3 * vertices.itemsize
    )
    gl.glEnableVertexAttribArray(1)

    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
    gl.glBindVertexArray(0)

    # 2. Update projection matrix uniform for the new size
    projection = _calculate_ortho_projection(g_frame_width, g_frame_height)
    gl.glUseProgram(g_shader_program)
    gl.glUniformMatrix4fv(g_projection_loc, 1, gl.GL_FALSE, projection)
    gl.glUseProgram(0)

    # 3. Allocate texture storage
    gl.glBindTexture(gl.GL_TEXTURE_2D, g_texture_id)
    gl.glTexImage2D(
        gl.GL_TEXTURE_2D,
        0,
        gl.GL_RGB,
        g_frame_width,
        g_frame_height,
        0,
        gl.GL_RGB,
        gl.GL_UNSIGNED_BYTE,
        None,
    )
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)


def main(args, stop_e: Event):
    global udp_receiver, stop_event, window, current_frame
    global \
        g_frame_width, \
        g_frame_height, \
        g_vao, \
        g_texture_id, \
        g_projection_loc, \
        g_shader_program

    g_frame_width = None
    g_frame_height = None

    stop_event = stop_e

    print("OpenGL render process (main) started. Initializing UDPReceiver and GLFW...")
    udp_receiver = net.UDPReceiver(
        conf.PROCESSING_HOST, conf.PROCESSING_PORT, timeout=0.01
    )

    if not glfw.init():
        print("Render: Failed to initialize GLFW.")
        stop_event.set()
        return

    glfw.window_hint(glfw.SAMPLES, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)  # Core Profile
    glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)  # macOS compatibility

    window = glfw.create_window(
        conf.DISPLAY_WIDTH,
        conf.DISPLAY_HEIGHT,
        "Multi-Process Video Stream (GLFW)",
        None,
        None,
    )
    if not window:
        print("Render: Failed to create GLFW window.")
        glfw.terminate()
        stop_event.set()
        return

    glfw.make_context_current(window)
    glfw.set_framebuffer_size_callback(window, _framebuffer_size_callback)
    glfw.swap_interval(1)  # V-Sync

    _init_opengl(conf.DISPLAY_WIDTH, conf.DISPLAY_HEIGHT)

    try:
        while not glfw.window_should_close(window) and not stop_event.is_set():
            glfw.poll_events()

            try:
                frame_from_receiver = udp_receiver.receive()

                if frame_from_receiver is net.EOS:
                    print("Render: Received EOS_SIGNAL from UDP. Shutting down GLFW.")
                    stop_event.set()
                    break

                if frame_from_receiver is not None:
                    current_frame = frame_from_receiver

                    # Initialize on first frame
                    if g_frame_width is None or g_frame_height is None:
                        initialize_first_frame(current_frame)

                    # Update texture data every frame
                    gl.glBindTexture(gl.GL_TEXTURE_2D, g_texture_id)
                    gl.glTexSubImage2D(
                        gl.GL_TEXTURE_2D,
                        0,
                        0,
                        0,
                        g_frame_width,
                        g_frame_height,
                        gl.GL_RGB,
                        gl.GL_UNSIGNED_BYTE,
                        current_frame.tobytes(),
                    )
                    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

            except socket.error as e:
                print(f"Render: Socket error receiving frame: {e}")
                stop_event.set()
                break
            except Exception as e:
                print(f"Render: Error processing received data: {e}")
                import traceback

                traceback.print_exc()
                stop_event.set()
                break

            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            # Rendering
            gl.glUseProgram(g_shader_program)

            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, g_texture_id)

            gl.glBindVertexArray(g_vao)
            gl.glDrawElements(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None)
            gl.glBindVertexArray(0)

            gl.glUseProgram(0)

            glfw.swap_buffers(window)

    finally:
        if g_shader_program:
            gl.glDeleteProgram(g_shader_program)
        if g_vao:
            gl.glDeleteVertexArrays(1, [g_vao])
        if g_texture_id:
            gl.glDeleteTextures(1, [g_texture_id])

        if udp_receiver:
            udp_receiver.close()
        if window:
            glfw.destroy_window(window)
        glfw.terminate()
        print("OpenGL render process exiting.")
