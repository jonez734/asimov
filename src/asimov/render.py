# my_project/processes/render.py

import cv2
import numpy as np
import OpenGL.GL as gl
import glfw 
from multiprocessing import Event
import time
import socket # For socket.error

from .net import UDPReceiver
from . import conf

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
