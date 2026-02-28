# my_project/processes/render.py

import numpy as np
import OpenGL.GL as gl
import glfw 
from multiprocessing import Event
import time
import socket
import ctypes

from asimov.net import UDPReceiver
from . import conf


def load_texture(image_path: str) -> int:
    """Load an image file as an OpenGL 2D texture."""
    from PIL import Image
    
    image = Image.open(image_path)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = np.array(image, dtype=np.uint8)
    
    texture = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_REPEAT)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_REPEAT)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR_MIPMAP_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, image.width, image.height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_data)
    gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
    
    return texture


def create_shader(vertex_source: str, fragment_source: str):
    """Compile vertex and fragment shaders and link into a program."""
    import OpenGL.GL.shaders
    
    shader = OpenGL.GL.shaders.compileProgram(
        OpenGL.GL.shaders.compileShader(vertex_source, gl.GL_VERTEX_SHADER),
        OpenGL.GL.shaders.compileShader(fragment_source, gl.GL_FRAGMENT_SHADER)
    )
    return shader


def create_cube(aspect_ratio: float = 1.0) -> tuple[int, int]:
    """Create a cube VAO with position and texture coordinates.

    Args:
        aspect_ratio: Width/height ratio (image_width/image_height).
                      Used to scale the cube depth for proper display.
    
    Returns:
        Tuple of (VAO handle, index count)
    """
    depth = 0.5 * aspect_ratio
    vertices = np.array([
        -0.5, -0.1, -depth,  0.0, 0.0,
         0.5, -0.1, -depth,  1.0, 0.0,
         0.5,  0.1, -depth,  1.0, 1.0,
        -0.5,  0.1, -depth,  0.0, 1.0,

        -0.5, -0.1,  depth,  0.0, 0.0,
         0.5, -0.1,  depth,  1.0, 0.0,
         0.5,  0.1,  depth,  1.0, 1.0,
        -0.5,  0.1,  depth,  0.0, 1.0,
    ], dtype=np.float32)
    
    indices = np.array([
        0, 1, 2, 2, 3, 0,
        4, 5, 6, 6, 7, 4,
        0, 1, 5, 5, 4, 0,
        2, 3, 7, 7, 6, 2,
        1, 2, 6, 6, 5, 1,
        3, 0, 4, 4, 7, 3
    ], dtype=np.uint32)
    
    vao = gl.glGenVertexArrays(1)
    gl.glBindVertexArray(vao)
    
    vbo = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
    
    ebo = gl.glGenBuffers(1)
    gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo)
    gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
    
    gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(0))
    gl.glEnableVertexAttribArray(0)
    
    gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_FALSE, 5 * vertices.itemsize, ctypes.c_void_p(3 * vertices.itemsize))
    gl.glEnableVertexAttribArray(1)
    
    return vao, len(indices)


VERTEX_SHADER = """#version 330 core
layout (location = 0) in vec3 position;
layout (location = 1) in vec2 texCoord;

uniform mat4 model;
uniform mat4 projection;

out vec2 TexCoord;

void main()
{
    gl_Position = projection * model * vec4(position, 1.0);
    TexCoord = texCoord;
}
"""

FRAGMENT_SHADER = """#version 330 core
in vec2 TexCoord;
out vec4 color;

uniform sampler2D texture1;

void main()
{
    color = texture(texture1, TexCoord);
}
"""

# Global variables
texture_id = None
current_frame = None
udp_receiver = None
stop_event = None
window = None

def _framebuffer_size_callback(window, width, height):
    """Callback for when the framebuffer is resized."""
    gl.glViewport(0, 0, width, height)
    _set_ortho_projection(width, height) # Re-apply projection for new size

# Custom simple gluOrtho2D equivalent using glOrtho
def _set_ortho_projection(width, height):
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    # Left, Right, Bottom, Top, Near, Far
    gl.glOrtho(0, width, height, 0, -1, 1) # Y-axis flipped for screen coordinates (top-left is 0,0)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

def _init_opengl(width, height):
    """Initializes OpenGL settings."""
    gl.glClearColor(0.0, 0.0, 0.0, 1.0) # Black background
    
    _set_ortho_projection(width, height)
    
    gl.glEnable(gl.GL_TEXTURE_2D)
    global texture_id
    texture_id = gl.glGenTextures(1)
    
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

def main(args, stop_e: Event):
    """
    Initializes GLFW and OpenGL, then runs the main render loop.
    This function is run as a separate process.
    """
    global udp_receiver, stop_event, window, texture_id
    stop_event = stop_e

    print("OpenGL render process started. Initializing UDPReceiver and GLFW...")
    udp_receiver = UDPReceiver(conf.PROCESSING_HOST, conf.PROCESSING_PORT, timeout=0.01)

    if not glfw.init():
        print("Render: Failed to initialize GLFW.")
        stop_event.set()
        return

    glfw.window_hint(glfw.SAMPLES, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_COMPAT_PROFILE) # glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)

    window = glfw.create_window(conf.DISPLAY_WIDTH, conf.DISPLAY_HEIGHT, "Multi-Process Video Stream (GLFW)", None, None)
    if not window:
        print("Render: Failed to create GLFW window.")
        glfw.terminate()
        stop_event.set()
        return

    glfw.make_context_current(window)
    glfw.set_framebuffer_size_callback(window, _framebuffer_size_callback)
    glfw.swap_interval(1) # VSync enabled

    _init_opengl(conf.DISPLAY_WIDTH, conf.DISPLAY_HEIGHT)

    last_frame_time = time.monotonic()

    try:
        while not glfw.window_should_close(window) and not stop_event.is_set():
            current_time = time.monotonic()
            delta_time = current_time - last_frame_time

            glfw.poll_events()

            # --- Frame Update Logic ---
            try:
                frame_from_receiver = udp_receiver.receive_next_complete_frame_or_signal()
                
                if frame_from_receiver is conf.EOS_SIGNAL:
                    print("Render: Received EOS_SIGNAL from UDP. Shutting down GLFW.")
                    stop_event.set()
                    break
                
                if frame_from_receiver is not None:
                    global current_frame
                    current_frame = frame_from_receiver # This frame is now already RGB and vertically flipped!
                    
                    # --- REMOVED: No more cv2.cvtColor or np.flipud calls here ---
                    # The incoming frame_from_receiver is already in the correct format for OpenGL.
                    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, 
                                    current_frame.shape[1], current_frame.shape[0], 0, 
                                    gl.GL_RGB, gl.GL_UNSIGNED_BYTE, current_frame.tobytes())
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

            # --- Drawing Logic ---
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            gl.glLoadIdentity()

            if current_frame is not None:
                gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
                gl.glBegin(gl.GL_QUADS)
                gl.glTexCoord2f(0, 0)
                gl.glVertex2f(0, 0)
                gl.glTexCoord2f(1, 0)
                gl.glVertex2f(conf.DISPLAY_WIDTH, 0)
                gl.glTexCoord2f(1, 1)
                gl.glVertex2f(conf.DISPLAY_WIDTH, conf.DISPLAY_HEIGHT)
                gl.glTexCoord2f(0, 1)
                gl.glVertex2f(0, conf.DISPLAY_HEIGHT)
                gl.glEnd()
            
            glfw.swap_buffers(window)
            
            last_frame_time = current_time

    finally:
        if udp_receiver:
            udp_receiver.close()
        if window:
            glfw.destroy_window(window)
        glfw.terminate()
        print("OpenGL render process exiting.")
