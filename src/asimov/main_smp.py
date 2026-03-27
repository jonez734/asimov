import warnings

warnings.warn(
    "asimov.main_smp is deprecated and unused. It will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2,
)

import cv2
import numpy as np
from multiprocessing import Process, Queue, Event
import time
import queue  # Import for queue.Empty exception

# PyGLFW for window management and PyOpenGL for OpenGL bindings
import glfw
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

from bbsengine6 import io

from . import conf

# --- Queues for Inter-Process Communication (declared globally for simplicity,
#     but passed as args to processes) ---
# NOTE: In a more complex module setup, you might pass these queues
# via a shared context object or similar, but global declaration is fine for this example.
frame_queue = Queue(maxsize=conf.QUEUESIZE)  # From Capture to Processing
opengl_input_queue = Queue(maxsize=conf.QUEUESIZE)  # From Processing to OpenGL Render

# --- Events for Signaling ---
stop_event = Event()


# --- (1) Video Capture Process ---
def video_capture_process(out_q, stop_e):
    cap = cv2.VideoCapture(0)  # 0 for default webcam
    if not cap.isOpened():
        io.echo(
            "Error: Could not open video stream in capture process. Signaling stop."
        )
        frame_q.put(None)
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf.CAP_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf.CAP_HEIGHT)
    if cap.set(cv2.CAP_PROP_FPS, conf.FPS) is False:
        io.echo(f"could not set FPS to {conf.FPS}")

    io.echo(
        f"Capture process started. Capturing at {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {int(cap.get(cv2.CAP_PROP_FPS))} FPS"
    )

    frame_count = 0
    current_retries = 0
    while not stop_e.is_set():  # Loop only while stop_e is NOT set
        ret, frame = cap.read()
        if ret:
            current_retries = 0
            try:
                # Try to put with a timeout. If the queue is full,
                # and stop_event is set, we'll quickly exit.
                out_q.put(frame, timeout=0.1)
                frame_count += 1
            except queue.Full:
                io.echo("out_q full")
                if stop_e.is_set():
                    break
        else:
            current_retries += 1
            if current_retries >= conf.FPS * 5:
                io.echo("too many retries waiting for camera", level="error")
                break
        time.sleep(0.01)

        io.echo(f"video_capture_process.200: {frame_count=}", level="debug")

    cap.release()

    try:
        out_q.put(
            None, timeout=1.0
        )  # Give it a bit more time to ensure sentinel gets through since we are about to exit
    except queue.Full:
        io.echo("Capture: Could not send sentinel to output queue (full).")

    io.echo("Capture process stopped.")
    return True


# --- (2) Image Processing Process (CPU-bound) ---
def image_processing_process(in_q, out_q):
    io.echo("Image processing process started.")
    while True:
        frame = None
        try:
            frame = in_q.get()
        except Exception as e:
            io.echo(f"image_processing_process exception: {e}")
            break

        if frame is None:
            io.echo(
                "Processing: Received sentinel (None). Signaling downstream and exiting."
            )
            # Important: Pass the sentinel down the pipeline if you have more stages.
            # Use a try-except to avoid blocking if the downstream queue is full
            # during shutdown, as the downstream consumer might have already exited.
            try:
                out_q.put(None, timeout=2.00)
            except queue.Full:
                io.echo(
                    "Processing: Output queue full during sentinel propagation, dropping sentinel."
                )

            break  # Exit the loop, as no more frames will arrive

        # --- Your CPU-based Image Processing Logic Here ---
        # Example: Convert to grayscale and back to BGR (required for OpenGL texture from OpenCV)
        #        processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #        processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR) # Convert back for display
        # Example: Apply a blur
        #        processed_frame = cv2.GaussianBlur(frame, (5, 5), 0)
        processed_frame = frame

        try:
            # Try to put the processed frame with a timeout.
            # If the output queue is full, it's generally better to drop a frame
            # than to block indefinitely, especially in a real-time system.
            out_q.put(processed_frame, timeout=0.1)
        except queue.Full:
            # This means the downstream process might be slow or has already stopped
            # and its queue is full. We drop the frame but continue processing
            # other incoming frames until we receive our own sentinel.
            io.echo("Processing: Output queue full, dropping processed frame.")
            time.sleep(0.001)
            continue  # drop frame and continue

    io.echo("Image processing process stopped.")


# --- (3) OpenGL Render and Effects Process ---
def opengl_render_process(in_q, stop_e):
    io.echo("OpenGL render and effects process started.")

    # --- GLFW Initialization ---
    if not glfw.init():
        io.echo("Error: Could not initialize GLFW")
        stop_e.set()
        return

    # Set window hints for OpenGL 3.3 Core Profile
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.RESIZABLE, glfw.FALSE)  # Fixed window size for simplicity

    window = glfw.create_window(
        conf.DISPLAY_WIDTH, conf.DISPLAY_HEIGHT, "asimov - cam0", None, None
    )
    if not window:
        glfw.terminate()
        io.echo("Error: Could not create GLFW window")
        stop_e.set()
        return

    glfw.make_context_current(window)
    glfw.swap_interval(1)  # Enable vsync (0 for no vsync)

    # --- Callback Functions for GLFW Events ---
    def key_callback(window, key, scancode, action, mods):
        if action == glfw.PRESS:
            if key == glfw.KEY_Q or key == glfw.KEY_ESCAPE:
                glfw.set_window_should_close(window, True)

    def window_close_callback(window):
        stop_e.set()  # Set stop_event on window close button
        io.echo("window_close_callback()")

    glfw.set_key_callback(window, key_callback)
    glfw.set_window_close_callback(window, window_close_callback)

    # Initialize OpenGL settings
    glViewport(0, 0, conf.DISPLAY_WIDTH, conf.DISPLAY_HEIGHT)
    glClearColor(0.0, 0.0, 0.0, 1.0)  # Black background

    # --- Shader Setup ---
    # Vertex Shader (simple pass-through)
    # Using modern GLSL syntax for Core Profile
    VERTEX_SHADER = """
    #version 330 core
    layout (location = 0) in vec3 aPos;
    layout (location = 1) in vec2 aTexCoord;

    out vec2 TexCoord;

    void main() {
        gl_Position = vec4(aPos, 1.0);
        TexCoord = aTexCoord;
    }
    """
    # Fragment Shader (simple texture display, you can add effects here)
    FRAGMENT_SHADER = """
    #version 330 core
    out vec4 FragColor;

    in vec2 TexCoord;

    uniform sampler2D ourTexture;

    void main() {
        FragColor = texture(ourTexture, TexCoord);
        // Example effect: simple color inversion
        // FragColor = vec4(1.0 - texture(ourTexture, TexCoord).rgb, 1.0);
    }
    """

    # Compile and Link Shaders
    vertex_shader_id = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader_id, VERTEX_SHADER)
    glCompileShader(vertex_shader_id)
    if not glGetShaderiv(vertex_shader_id, GL_COMPILE_STATUS):
        io.echo(
            "Vertex shader compile error:",
            glGetShaderInfoLog(vertex_shader_id).decode(),
        )

    fragment_shader_id = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader_id, FRAGMENT_SHADER)
    glCompileShader(fragment_shader_id)
    if not glGetShaderiv(fragment_shader_id, GL_COMPILE_STATUS):
        io.echo(
            "Fragment shader compile error:",
            glGetShaderInfoLog(fragment_shader_id).decode(),
        )

    program_id = glCreateProgram()
    glAttachShader(program_id, vertex_shader_id)
    glAttachShader(program_id, fragment_shader_id)
    glLinkProgram(program_id)
    if not glGetProgramiv(program_id, GL_LINK_STATUS):
        io.echo("Shader program link error:", glGetProgramInfoLog(program_id).decode())

    glDeleteShader(vertex_shader_id)
    glDeleteShader(fragment_shader_id)

    glUseProgram(program_id)

    # --- Vertices and Texture Coordinates for a Fullscreen Quad ---
    # (x, y, z, u, v)
    vertices = np.array(
        [
            -1.0,
            -1.0,
            0.0,
            0.0,
            0.0,  # Bottom-left
            1.0,
            -1.0,
            0.0,
            1.0,
            0.0,  # Bottom-right
            1.0,
            1.0,
            0.0,
            1.0,
            1.0,  # Top-right
            -1.0,
            1.0,
            0.0,
            0.0,
            1.0,  # Top-left
        ],
        dtype=np.float32,
    )

    indices = np.array(
        [
            0,
            1,
            2,  # First Triangle
            2,
            3,
            0,  # Second Triangle
        ],
        dtype=np.uint32,
    )

    # Setup VAO, VBO, EBO
    VAO = glGenVertexArrays(1)
    VBO = glGenBuffers(1)
    EBO = glGenBuffers(1)

    glBindVertexArray(VAO)

    glBindBuffer(GL_ARRAY_BUFFER, VBO)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    # Position attribute
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    # Texture coordinate attribute
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
    glEnableVertexAttribArray(1)

    # Create a single texture ID
    texture_id = glGenTextures(1)
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    # Set texture parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    # --- FPS Calculation Variables ---
    frame_count = 0
    start_time = time.time()
    fps_display_interval = 0.5  # Update FPS every 1 second

    # --- Main Rendering Loop ---
    # Loop while the window is not requested to close and our stop_event is not set
    while not glfw.window_should_close(window) and not stop_e.is_set():
        glfw.poll_events()  # Process events

        frame = None
        try:
            # Try to get with a timeout. This allows periodic check of stop_e.
            frame = in_q.get(timeout=0.001)  # Shorter timeout for smoother display
        except queue.Empty:
            io.echo("opengl_render_process.140: queue empty")
            time.sleep(0.010)
            continue
        except Exception as e:
            io.echo(f"asimov.opengl_render_process.100: {e}", level="error")
            break

        if frame is None:
            io.echo("asimov.opengl_render_process.120: sentinel")
            break

        # --- OpenGL Rendering Logic ---
        # OpenCV frame needs to be converted to RGB for OpenGL
        # Note: Flip vertically because OpenGL texture origin is bottom-left, OpenCV is top-left
        # If you prefer not to flip CPU-side, you can change TexCoord.t = 1.0 - TexCoord.t in shader
        frame = cv2.flip(frame, 0)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Bind the texture and upload frame data
        glBindTexture(GL_TEXTURE_2D, texture_id)
        # Using GL_RGB as internal format and format of pixel data
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            frame.shape[1],
            frame.shape[0],
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            frame.tobytes(),
        )

        glClear(GL_COLOR_BUFFER_BIT)  # Clear the color buffer

        glUseProgram(program_id)  # Activate shader program
        glBindVertexArray(VAO)  # Bind the vertex array object
        glDrawElements(
            GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, None
        )  # Draw the quad

        glfw.swap_buffers(window)  # Swap front and back buffers

        # --- FPS Calculation and Display ---
        frame_count += 1
        current_time = time.time()
        if current_time - start_time >= fps_display_interval:
            fps = frame_count / (current_time - start_time)
            glfw.set_window_title(window, f"Live OpenGL Stream - FPS: {fps:.2f}")
            frame_count = 0
            start_time = current_time

    # --- Cleanup OpenGL and GLFW Resources ---
    glDeleteVertexArrays(1, [VAO])
    glDeleteBuffers(1, [VBO])
    glDeleteBuffers(1, [EBO])
    glDeleteTextures(1, [texture_id])
    glDeleteProgram(program_id)

    glfw.destroy_window(window)
    glfw.terminate()
    io.echo("OpenGL render and effects process stopped.")


# --- Main Execution Function ---
def main(args=None, **kwargs):
    io.echo("Starting main application...")

    processes = []

    # Create processes
    p_capture = Process(
        target=video_capture_process,
        args=(frame_queue, stop_event),
        name="VideoCapture",
    )
    # p_capture = libasimov.runmodule(args, "p_videocapture", out_q=frame_queue, stop_event=stop_event)
    # if p_capture is False:
    #    io.echo(f"failed to start p_capture ({p_capture=})", level="error")
    #    return False
    p_processing = Process(
        target=image_processing_process,
        args=(frame_queue, opengl_input_queue),
        name="Processing",
    )
    p_opengl_render = Process(
        target=opengl_render_process,
        args=(opengl_input_queue, stop_event),
        name="OpenGLRender",
    )

    processes.extend([p_capture, p_processing, p_opengl_render])

    # Start processes
    for p in processes:
        p.start()

    io.echo("All processes started. Close the OpenGL window or press 'q' to quit.")

    # The OpenGL process is responsible for setting the stop_event
    # We wait for it to finish its work and exit
    p_opengl_render.join()

    # Once render process has exited (and set stop_event), ensure all others get the signal
    # This might be redundant if opengl_render_process already set it, but harmless.
    # if not stop_event.is_set():
    #    stop_event.set() # Just in case it exited for another reason

    # Wait for all other processes to terminate cleanly
    exit_code = 0
    for p in processes:
        if p.is_alive():  # Only join if it's still running
            io.echo(f"Waiting for {p.name} to terminate...")
            p.join(timeout=5)  # Give it a timeout in case it's truly stuck
            if p.is_alive():
                io.echo(
                    f"Warning: {p.name} did not terminate cleanly. Terminating forcefully."
                )
                p.terminate()  # Forceful termination as a last resort
                p.join()  # Wait for termination
                exit_code = 1  # Indicate an error in shutdown

    io.echo("All processes checked. Application finished.")
    return exit_code  # Return 0 for success, 1 for errors during shutdown


def init(args=None, **kwargs):
    """
    Initializes any necessary components for the module.
    :param args: Placeholder for command-line arguments.
    :param kwargs: Additional keyword arguments.
    :return: True if initialization is successful, False otherwise.
    """
    io.echo("Module init() called.")
    # No specific initialization needed here for this example,
    # as multiprocessing components are set up in main().
    return True


def access(args=None, op=None, **kwargs):
    """
    Provides a generic access point for operations.
    :param args: Placeholder for command-line arguments or other data.
    :param op: The operation to perform (e.g., 'start', 'stop').
    :param kwargs: Additional keyword arguments.
    :return: True if operation is successful, False otherwise.
    """
    return True


def buildargs(args=None, **kwargs):
    """
    Builds and returns arguments, typically for a command-line parser.
    :param args: Placeholder for initial arguments.
    :param kwargs: Additional keyword arguments.
    :return: An object containing arguments, or None if not applicable.
    """
    io.echo("Module buildargs() called.")
    # In a real scenario, this might return an argparse.ArgumentParser instance
    # or parse default arguments.
    return None
