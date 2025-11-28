from OpenGL.GL import *
from OpenGL.GLUT import *

from math import log2, ceil
import struct
from dataclasses import dataclass, field
import time

import numpy as np

from . import io
from .common import safe_path

import cv2
from typing import Callable, Any, Tuple

MAX_BLOCK_SIZE = 128

LOGGER_NAME = "asimov"

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


@dataclass
class Block:
    id: int             # Unique identifier for the block
    length: int         # Length of stored data
    data: bytes         # The data (raw if uncompressed, compressed otherwise)

BLOCK_HEADER_FORMAT = "!HH"  # block_id (2 bytes), data_len (2 bytes)
BLOCK_HEADER_SIZE = struct.calcsize(BLOCK_HEADER_FORMAT)

def encode_block(block: Block, compress=False) -> bytes:
    """
    Encodes a single frame block into a binary format suitable for network transmission.

    The encoded format consists of:
    - 2 bytes: block_id (unsigned short, big-endian)
    - 1 byte: compressed flag (0 or 1)
    - 2 bytes: length of block data in bytes (unsigned short)
    - N bytes: block data itself

    Parameters:
    - block (dict): A dictionary with the following keys:
        - 'block_id' (int): Identifier of the block (0–65535).
        - 'compressed' (bool): Whether the block data is compressed.
        - 'data' (bytes): The raw or compressed data for this block.

    Returns:
    - bytes: The binary-encoded block, including header and data.

    Raises:
    - ValueError: If the block is missing required fields, types are incorrect, or data is too large.
    """
    try:
        block_id = block.id
        data = block.data
    except KeyError as e:
        raise ValueError(f"Missing required block field: {e.args[0]}") from e

    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("block['data'] must be bytes or bytearray")
    if not isinstance(block_id, int) or not (0 <= block_id <= 0xFFFF):
        raise ValueError("block_id must be an int between 0 and 65535")

    data_len = len(data)
    if data_len > 0xFFFF:
        raise ValueError("Block data is too large (must be <= 65535 bytes)")

    header = struct.pack(BLOCK_HEADER_FORMAT, block_id, data_len)
    return header + data

def decode_block(data: bytes, block_size: int, channels: int = 3) -> tuple[int, np.ndarray]:
    """
    Decode a frame block from bytes into a NumPy array.

    The function expects the input data to be structured as:
    - 2 bytes: block_id (unsigned short, H)
    - 1 byte: compressed flag (unsigned char, B)
    - 2 bytes: block length in bytes (unsigned short, H)
    - N bytes: block data (length specified above)

    Parameters:
        data (bytes): The raw byte string to decode.
        block_size (int): The width and height of the square image block.
        channels (int): The number of color channels per pixel (default: 3).

    Returns:
        tuple[int, np.ndarray]: A tuple containing the block_id and the decoded image block
                                reshaped as (block_size, block_size, channels).

    Raises:
        ValueError: If the decompressed length does not match block_size * block_size * channels.
    """
    header_size = struct.calcsize(FRAME_BLOCK_FORMAT)
    block_id, compressed, block_len = struct.unpack_from(FRAME_BLOCK_FORMAT, data)
    block_data = data[header_size:header_size + block_len]

    if compressed:
        block_data = zlib.decompress(block_data)

    expected_len = block_size * block_size * channels
    if len(block_data) != expected_len:
        raise ValueError(f"Expected {expected_len} bytes, got {len(block_data)}")

    array = np.frombuffer(block_data, dtype=np.uint8)
    return block_id, array.reshape((block_size, block_size, channels))

def block_id_to_xy(block_id, frame_width, block_size):
    cols = frame_width // block_size
    row = block_id // cols
    col = block_id % cols
    return col * block_size, row * block_size

def find_best_power_of_two_block_size(h, w):
    """
    Returns the largest power-of-two block side length that evenly divides both h and w.
    Also returns the corresponding block size (side**2).
    """
    for i in reversed(range(1, int(log2(MAX_BLOCK_SIZE)) + 1)):
        side = 2 ** i
        if h % side == 0 and w % side == 0:
            return side
    raise ValueError(f"No valid block size found for given dimensions {h=} {w=}")

def get_changed_blocks(frame, previous_frame, frame_id, compress=True):
    """
    Detects changed blocks and returns a list of dicts with metadata:
    - frame_id: int
    - block_id: int
    - block: compressed bytes (if compress=True)
    - total_changed: total number of changed blocks (for reassembly)
    """
    if frame.shape != previous_frame.shape:
        raise ValueError("Frame sizes do not match")

    if np.array_equal(frame, previous_frame):
        return []  # No changes

    h, w, _ = frame.shape
    block_size = find_best_power_of_two_block_size(h, w)

    cols = w // block_size
    rows = h // block_size

    changed_blocks = []

    for block_id in range(rows * cols):
        row = block_id // cols
        col = block_id % cols
        y, x = row * block_size, col * block_size

        block = frame[y:y+block_size, x:x+block_size]
        prev_block = previous_frame[y:y+block_size, x:x+block_size]

        if not np.array_equal(block, prev_block):
            data = block.tobytes()

            changed_blocks.append(Block(id=block_id, length=len(data), data=data))

    return changed_blocks

def calculate_total_blocks_in_frame(frame_width, frame_height, block_size):
    cols = ceil(frame_width / block_size)
    rows = ceil(frame_height / block_size)
    return cols * rows

def _blend_bgr(img_bgr, overlay_bgr, alpha_mask):
    """Blend overlay_bgr into img_bgr using per-pixel alpha_mask (0..1). In-place."""
    # alpha_mask: (h,w) float32 0..1
    a = alpha_mask[..., None]  # (h,w,1)
    img_f = img_bgr.astype(np.float32)
    over_f = overlay_bgr.astype(np.float32)
    out = over_f * a + img_f * (1.0 - a)
    np.copyto(img_bgr, np.clip(out, 0, 255).astype(np.uint8))


def _composite_rgba(img_rgba, overlay_bgr, overlay_a):
    """
    Proper alpha-composite overlay_bgr (with overlay_a 0..1) over img_rgba (BGRA).
    In-place.
    """
    img_c = img_rgba[..., :3].astype(np.float32)
    img_a = img_rgba[..., 3].astype(np.float32) / 255.0

    over_c = overlay_bgr.astype(np.float32)
    over_a = overlay_a.astype(np.float32)

    # new alpha per pixel
    new_a = over_a + img_a * (1.0 - over_a)

    # premultiplied result colors
    out_premul = over_c * over_a[..., None] + img_c * (img_a * (1.0 - over_a))[..., None]

    # un-premultiply where new_a > 0
    result_c = np.zeros_like(out_premul, dtype=np.float32)
    mask = new_a > 1e-8
    result_c[mask] = out_premul[mask] / new_a[mask, None]

    img_rgba[..., :3] = np.clip(result_c, 0, 255).astype(np.uint8)
    img_rgba[..., 3] = np.clip(new_a * 255.0, 0, 255).astype(np.uint8)


def draw_text(img, x, y, text,
              color=(255, 255, 255), alpha=1.0,
              shadow_offset=1, shadow_color=(128, 128, 128), shadow_alpha=1.0,
              thickness=1, font_scale=0.5,
              font=cv2.FONT_HERSHEY_SIMPLEX):

    is_rgba = (img.shape[2] == 4)
    h, w = img.shape[:2]

#    print(f"{is_rgba=} {h=} {w=}")

    def make_overlay_and_mask(tx, ty, col):
        """Draw text onto a blank image and return overlay + alpha mask."""
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(overlay, text, (tx, ty), font, font_scale,
                    tuple(int(c) for c in col[:3]), thickness, cv2.LINE_AA)
        mask = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY) > 0
        return overlay, mask.astype(np.float32)

    def blend_bgr(dst, overlay, mask, alpha_val):
        """Blend overlay into dst only where mask is nonzero."""
        m = (mask * alpha_val)[..., None]
        dst[:] = (overlay * m + dst * (1 - m)).astype(np.uint8)

    def blend_rgba(dst, overlay, mask, alpha_val):
        """Blend overlay into BGRA image."""
        m = (mask * alpha_val)[..., None]
        dst_rgb = dst[..., :3].astype(np.float32)
        over_rgb = overlay.astype(np.float32)
        dst[..., :3] = (over_rgb * m + dst_rgb * (1 - m)).astype(np.uint8)
        # Leave alpha channel unchanged (we could modify if desired)

    # --- Draw shadow ---
    if shadow_offset != 0 and (isinstance(shadow_offset, tuple) or shadow_offset != 0):
        if isinstance(shadow_offset, int):
            sx, sy = shadow_offset, shadow_offset
        else:
            sx, sy = shadow_offset
        shadow_overlay, shadow_mask = make_overlay_and_mask(x + sx, y + sy, shadow_color)
        if not is_rgba:
            blend_bgr(img, shadow_overlay, shadow_mask, shadow_alpha)
        else:
            blend_rgba(img, shadow_overlay, shadow_mask, shadow_alpha)

    # --- Draw main text ---
    text_overlay, text_mask = make_overlay_and_mask(x, y, color)
    if not is_rgba:
        blend_bgr(img, text_overlay, text_mask, alpha)
    else:
        blend_rgba(img, text_overlay, text_mask, alpha)

    return img

def get_bottom_right_position(frame, text, font, font_scale=1.0, thickness=2, padding=10):
    """
    Calculate (x, y) starting position to draw text in the lower-right corner with padding.

    Returns:
        (x, y): Baseline start point for cv2.putText().
    """
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    frame_height, frame_width = frame.shape[:2]

    # x is left edge of text so that right edge is at (frame_width - padding)
    x = frame_width - padding - text_width
    # y is the baseline so that bottom of text is at (frame_height - padding)
    y = frame_height - padding - baseline

    return x, y

def get_device_by_label(label:str):
    base = "/sys/class/video4linux"
    for dev in os.listdir(base):
        card_path = safe_path(base, dev, "name")
        io.echo(f"get_device_by_label.100: {card_path=}")
        try:
            with open(card_path, "r") as f:
                name = f.read().strip()
            if name == label:
                return f"/dev/{dev}"
        except FileNotFoundError:
            continue
    return None

#path = find_device_by_label("PyVirtualCam")
#if path:
#    print("Found:", path)
#else:
#    print("Not found")

def camera_ready(cap, timeout=5):
    start_time = time.time()
    while True:
        ret, frame = cap.read()
        if frame is not None:
            return True  # Camera gave a valid frame
        print("waiting...")
        if time.time() - start_time >= timeout:
            print("camera_ready(): timeout")
            return False  # Timeout reached, return failure
        time.sleep(0.1)  # Avoid busy waiting



def heading(title:str, level=1, **kwargs): # hrchar:str="{acs:hline}", llcorner="{acs:llcorner}", lrcorner="{acs:lrcorner}", ulcorner="{acs:ulcorner}", urcorner="{acs:urcorner}", vline="{acs:vline}", width=None, fillchar=" ", center=True):
##  if io.getoption("style", "ttyio") == "noansi":
##      width = 100
##      hline="-"*width
##      llcorner="+"
##      lrcorner="+"
##      ulcorner="+"
##      urcorner="+"
##      vline="|"
##      #boxcolor = ""
##      #titlecolor = ""
##      #reset = ""
##  else:
  width = io.terminal.width() - 4
  w = width - len(title)
  if int(w % 2) == 0:
    repeat = int(w/2)
    leftpadding  = " "*int(repeat)
    rightpadding = " "*int(repeat)
  else:
    repeat = int(w-2)/2
    leftpadding  = " "*int(repeat+2)
    rightpadding = " "*int(repeat+1)

  io.echo(f"{{/all}}{{normalcolor}} {{boxcolor}}{{ulcorner}}{{hline:{width}}}{{urcorner}}", wordwrap=False, end="\n")
  io.echo(f" {{boxcolor}}{{vline}}{{titlecolor}}{leftpadding}{title}{rightpadding}{{/all}}{{boxcolor}}{{vline}}", wordwrap=False, end="\n")
  io.echo(f" {{llcorner}}{{hline:{width}}}{{lrcorner}}{{/all}}{{f6}}", wordwrap=False, end="")
  return

import math
import time
import cv2
import numpy as np

class OneEuroFilter:
    """
    One Euro Filter: https://cristal.univ-lille.fr/~casiez/1euro/
    Keeps smooth values but reacts faster to quick movements.

    Parameters:
    - freq (float): Estimated frequency/frame rate in Hz.
    - min_cutoff (float): Base smoothing factor (lower = more smooth).
    - beta (float): Factor that controls responsiveness to speed (higher = more responsive).
    - dcutoff (float): Cutoff frequency for the derivative filter.
    - init (float | None): Initial value.
    """
    def __init__(self, freq=30, min_cutoff=1.0, beta=0.01, dcutoff=1.0, init=None):
        self.freq = freq              # Hz, frame rate estimate
        self.min_cutoff = min_cutoff  # baseline smoothing
        self.beta = beta              # speed sensitivity
        self.dcutoff = dcutoff        # derivative smoothing
        self.last_time = None
        self.x_prev = init
        self.dx_prev = 0

    def _alpha(self, cutoff, dt):
        """Calculates the smoothing factor based on cutoff frequency and time step."""
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def update(self, x):
        """Applies the filter to the new value x."""
        now = time.time()
        if self.last_time is None:
            dt = 1.0 / self.freq
        else:
            dt = max(now - self.last_time, 1e-6)
        self.last_time = now

        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0

        # Derivative calculation
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.dcutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        # Adaptive cutoff calculation
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)

        # Filtered value
        x_hat = a * x + (1 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat

def get_centroid(pts: np.ndarray):
    """
    Calculates the centroid (center of mass) of a contour or set of points.

    Args:
        pts (np.ndarray): A numpy array of points (e.g., shape (N, 2) or (N, 1, 2)).

    Returns:
        tuple[float, float]: (cx, cy) coordinates of the centroid.
    """
    # Ensure points are in the correct format for cv2.moments
    if pts.ndim == 3:
        pts = pts.reshape(-1, 2)

    M = cv2.moments(pts)

    if M["m00"] == 0:
        return 0.0, 0.0

    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    return cx, cy

def blend_alpha(foreground_bgr: np.ndarray, background_bgr: np.ndarray, alpha_channel: np.ndarray) -> np.ndarray:
    """
    Blends a foreground image onto a background image using a separate alpha channel.

    This implements the formula: final = (alpha * foreground) + ((1 - alpha) * background).
    
    Args:
        foreground_bgr: The BGR color layer of the foreground (e.g., the trail), dtype float.
        background_bgr: The BGR color layer of the background (e.g., live cam), dtype float.
        alpha_channel: The alpha channel (0.0 to 1.0), dtype float.

    Returns:
        The blended image as a NumPy array (dtype np.uint8).
    """
    # 1. Prepare alpha for broadcasting (3 channels)
    alpha_3ch = cv2.merge([alpha_channel, alpha_channel, alpha_channel])

    # 2. Apply the blending formula
    blended_img_float = (alpha_3ch * foreground_bgr) + ((1 - alpha_3ch) * background_bgr)

    # 3. Convert back to standard image format
    return blended_img_float.astype(np.uint8)

# Example use:
# blended_frame = blend_alpha(trail_bgr.astype(float), img.astype(float), alpha_channel_normalized)


def safe_bgra_draw(canvas_bgra: np.ndarray, draw_func: Callable[..., Any], *args, **kwargs) -> np.ndarray:
    """
    Safely executes an OpenCV drawing function on a BGRA canvas by splitting
    and merging channels to ensure contiguous memory access.

    Args:
        canvas_bgra: The 4-channel BGRA canvas to draw on.
        draw_func: The OpenCV drawing function to execute (e.g., cv2.line, cv2.circle).
        *args, **kwargs: Arguments to pass directly to the draw_func.

    Returns:
        The modified 4-channel BGRA canvas.
    """
    if canvas_bgra.shape[2] != 4:
        raise ValueError("Input canvas must be a 4-channel BGRA array.")

    # 1. Split the canvas into 4 contiguous channels
    B, G, R, A = cv2.split(canvas_bgra)
    bgr_canvas_temp = cv2.merge((B, G, R)) # Create contiguous BGR slice

    # 2. Execute the drawing function on the contiguous BGR slice
    # Note: If drawing on Alpha is needed, it must be done separately on channel 'A'.
    # This example focuses on BGR drawing. The output of draw_func is often None (in-place modification).
    draw_func(bgr_canvas_temp, *args, **kwargs)

    # 3. Merge the modified BGR channels back
    B_new, G_new, R_new = cv2.split(bgr_canvas_temp)
    return cv2.merge((B_new, G_new, R_new, A))

# Example Use:
# canvas = safe_bgra_draw(canvas, cv2.circle, (100, 100), 20, (255, 0, 0), -1)

def apply_layer_fade(canvas: np.ndarray, decay_rate: float) -> np.ndarray:
    """
    Applies a temporal decay (fade-out) effect to a layer by blending it with black.

    Args:
        canvas: The image layer (e.g., trail canvas) to modify.
        decay_rate: The persistence factor (e.g., 0.95 for slow fade, 0.5 for fast fade).

    Returns:
        The faded image layer.
    """
    # Create a black image of the same shape and type
    black_layer = np.zeros_like(canvas)

    # Blend the existing canvas with black. (1 - decay_rate) is the black weight.
    faded_canvas = cv2.addWeighted(
        canvas,
        decay_rate,                 # Weight for the existing canvas
        black_layer,
        1.0 - decay_rate,           # Weight for the black layer
        0                           # Gamma correction (none)
    )
    return faded_canvas

# Example Use:
# trail_canvas = apply_layer_fade(trail_canvas, 0.95)

def interpolate_sequential(index: int, total_length: int, start_value: float, end_value: float) -> float:
    """
    Maps an element's index in a sequence to a proportional value between two endpoints.

    Args:
        index: The current position/age of the element (e.g., 1 to total_length).
        total_length: The maximum length of the sequence (e.g., MAX_TRAIL_LENGTH).
        start_value: The value corresponding to the start/oldest element (index 0 or 1).
        end_value: The value corresponding to the end/newest element (total_length).

    Returns:
        The interpolated value.
    """
    # Ensure index is within bounds for interpolation
    if index <= 0 or total_length <= 1:
        return start_value # Or handle error

    # Use numpy.interp to map the index within the [1, total_length] range
    # to the [start_value, end_value] range.
    return np.interp(index, [1, total_length], [start_value, end_value])

# Example Use:
# thickness = interpolate_sequential(i, MAX_TRAIL_LENGTH, 1.0, 8.0)
