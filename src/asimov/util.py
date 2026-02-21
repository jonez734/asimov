from OpenGL.GL import *
from OpenGL.GLUT import *

from math import log2, ceil, pi
import struct
import zlib
import os
import math
from dataclasses import dataclass, field
import time

import numpy as np

from . import io, conf
from .common import safe_path
from .io.echo import echo_traceback

import cv2
from typing import Callable, Any, Tuple, List, Optional, Sequence, Dict, Union

MAX_BLOCK_SIZE = 128

LOGGER_NAME = "asimov"

FRAME_BLOCK_FORMAT = "!HBBH"

def _normalize_color(c: Sequence[float]) -> Tuple[float, float, float, float]:
    """Normalize color tuple to 0.0-1.0 range."""
    if len(c) != 4:
        raise ValueError(f"Color tuple must have 4 values, got {len(c)}")
    return tuple(max(0.0, min(1.0, v / 255.0 if v > 1.0 else v)) for v in c)

def _get_shadow_offsets(offsets: Optional[List[Tuple[float, float]]] = None) -> List[Tuple[float, float]]:
    """Get default or custom shadow offsets."""
    if offsets is None:
        return [(-0.005, 0), (0.005, 0), (0, -0.005), (0, 0.005)]
    return offsets

# @since 20250326
def render_text(
    text: Optional[str],
    x: float,
    y: float,
    font: Any = GLUT_BITMAP_8_BY_13,
    color: Sequence[float] = (0.0, 1.0, 0.0, 1.0),
    shadow_color: Optional[Sequence[float]] = (0.0, 0.0, 0.0, 0.5),
    offsets: Optional[List[Tuple[float, float]]] = None,
) -> None:
    """
    Render bitmap text using OpenGL at a specific position with optional shadow effect.

    Parameters:
        text: The text to render. Can be None (no-op).
        x: X position in normalized OpenGL coordinates.
        y: Y position in normalized OpenGL coordinates.
        font: GLUT font (default: GLUT_BITMAP_8_BY_13).
        color: RGBA color for the text. Values can be 0.0-1.0 or 0-255 (default: Green).
        shadow_color: RGBA color for the shadow (default: Black with 50% opacity).
        offsets: List of (x_offset, y_offset) for shadow rendering.
    """
    if text is None or not isinstance(text, str) or text == "":
        return

    shadow_offsets = _get_shadow_offsets(offsets)
    normalized_color = _normalize_color(color)

    def _render(txt: str, px: float, py: float, ft: Any, col: Tuple[float, float, float, float]) -> None:
        glRasterPos2f(px, py)
        glColor4f(*col)
        for char in txt:
            glutBitmapCharacter(ft, ord(char))

    was_blend_enabled = glIsEnabled(GL_BLEND)
    prev_color = glGetFloatv(GL_CURRENT_COLOR)

    try:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPushMatrix()
        glLoadIdentity()

        if shadow_color:
            shadow = _normalize_color(shadow_color)
            for ox, oy in shadow_offsets:
                _render(text, x + ox, y + oy, font, shadow)

        _render(text, x, y, font, normalized_color)

        glPopMatrix()

        if not was_blend_enabled:
            glDisable(GL_BLEND)
        glColor4f(*prev_color)

    except Exception as e:
        if not was_blend_enabled:
            glDisable(GL_BLEND)
        glColor4f(*prev_color)
        echo_traceback(f"render_text() failed: {e}")

def render_quad(texture_id: int) -> None:
    """Render a quad with the given texture."""
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

def create_texture() -> int:
    """Create an OpenGL texture and return its ID."""
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glBindTexture(GL_TEXTURE_2D, 0)
    return texture_id

def update_texture(texture_id: int, frame: Optional[np.ndarray]) -> None:
    """Upload a BGR frame (e.g. from OpenCV) as a GL texture."""
    if frame is None:
        return

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, _ = frame_rgb.shape

    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, frame_rgb)
    glBindTexture(GL_TEXTURE_2D, 0)


@dataclass
class Block:
    id: int
    length: int
    data: bytes

BLOCK_HEADER_FORMAT = "!HH"  # block_id (2 bytes), data_len (2 bytes)
BLOCK_HEADER_SIZE = struct.calcsize(BLOCK_HEADER_FORMAT)

def encode_block(block: Block, compress: bool = False) -> bytes:
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

def block_id_to_xy(block_id: int, frame_width: int, block_size: int) -> Tuple[int, int]:
    """Convert block ID to x, y pixel coordinates."""
    cols = frame_width // block_size
    row = block_id // cols
    col = block_id % cols
    return col * block_size, row * block_size

def find_best_power_of_two_block_size(h: int, w: int) -> int:
    """
    Returns the largest power-of-two block side length that evenly divides both h and w.
    Also returns the corresponding block size (side**2).
    """
    for i in reversed(range(1, int(log2(MAX_BLOCK_SIZE)) + 1)):
        side = 2 ** i
        if h % side == 0 and w % side == 0:
            return side
    raise ValueError(f"No valid block size found for given dimensions {h=} {w=}")

def get_changed_blocks(
    frame: np.ndarray,
    previous_frame: np.ndarray,
    frame_id: int,
    compress: bool = True,
) -> List[Block]:
    """
    Detects changed blocks and returns a list of Block objects.

    Parameters:
        frame: Current frame
        previous_frame: Previous frame
        frame_id: ID of the current frame
        compress: Whether to compress block data

    Returns:
        List of Block objects with changed data
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

def calculate_total_blocks_in_frame(frame_width: int, frame_height: int, block_size: int) -> int:
    """Calculate total number of blocks in a frame."""
    cols = ceil(frame_width / block_size)
    rows = ceil(frame_height / block_size)
    return cols * rows

def _blend_bgr(img_bgr: np.ndarray, overlay_bgr: np.ndarray, alpha_mask: np.ndarray) -> None:
    """Blend overlay_bgr into img_bgr using per-pixel alpha_mask (0..1). In-place."""
    a = alpha_mask[..., None]
    img_f = img_bgr.astype(np.float32)
    over_f = overlay_bgr.astype(np.float32)
    out = over_f * a + img_f * (1.0 - a)
    np.copyto(img_bgr, np.clip(out, 0, 255).astype(np.uint8))


def _composite_rgba(img_rgba: np.ndarray, overlay_bgr: np.ndarray, overlay_a: np.ndarray) -> None:
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


def draw_text(
    img: np.ndarray,
    x: int,
    y: int,
    text: str,
    color: Tuple[int, int, int] = (255, 255, 255),
    alpha: float = 1.0,
    shadow_offset: Union[int, Tuple[int, int]] = 1,
    shadow_color: Tuple[int, int, int] = (128, 128, 128),
    shadow_alpha: float = 1.0,
    thickness: int = 1,
    font_scale: float = 0.5,
    font: int = cv2.FONT_HERSHEY_SIMPLEX,
) -> np.ndarray:
    """
    Draw text on an image with optional shadow and alpha blending.

    Parameters:
        img: The image to draw on (BGR or BGRA)
        x, y: Text position
        text: Text string to draw
        color: RGB color tuple
        alpha: Alpha blending factor (0-1)
        shadow_offset: Shadow offset (int or tuple)
        shadow_color: Shadow RGB color
        shadow_alpha: Shadow alpha
        thickness: Text thickness
        font_scale: Font scale
        font: OpenCV font

    Returns:
        The modified image
    """

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

def get_bottom_right_position(
    frame: np.ndarray,
    text: str,
    font: int,
    font_scale: float = 1.0,
    thickness: int = 2,
    padding: int = 10,
) -> Tuple[int, int]:
    """
    Calculate (x, y) starting position to draw text in the lower-right corner with padding.

    Returns:
        (x, y): Baseline start point for cv2.putText().
    """
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    frame_height, frame_width = frame.shape[:2]

    x = frame_width - padding - text_width
    y = frame_height - padding - baseline

    return x, y

def get_device_by_label(label: str) -> Optional[str]:
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
    def __init__(
        self,
        freq: float = 30,
        min_cutoff: float = 1.0,
        beta: float = 0.01,
        dcutoff: float = 1.0,
        init: Optional[float] = None,
    ) -> None:
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.last_time: Optional[float] = None
        self.x_prev: Optional[float] = init
        self.dx_prev: float = 0

    def _alpha(self, cutoff: float, dt: float) -> float:
        """Calculates the smoothing factor based on cutoff frequency and time step."""
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def update(self, x: float) -> float:
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

def get_centroid(pts: np.ndarray) -> Tuple[float, float]:
    """
    Calculates the centroid (center of mass) of a contour or set of points.

    Args:
        pts: A numpy array of points (e.g., shape (N, 2) or (N, 1, 2)).

    Returns:
        (cx, cy) coordinates of the centroid.
    """
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
    if index <= 0 or total_length <= 1:
        return start_value

    result = np.interp(index, [1, total_length], [start_value, end_value])
    return float(result)

# Example Use:
# thickness = interpolate_sequential(i, MAX_TRAIL_LENGTH, 1.0, 8.0)

def draw_diagnostics_overlay(frame: np.ndarray, diagnostics: Dict[str, float]) -> None:
    """Draw diagnostics overlay on a GL frame."""
    y_offset = 30
    for key, val in diagnostics.items():
        text = f"{key}: {val:.2f}"
        render_text(text, 10, y_offset, color=(0, 255, 255, 1.0))
        y_offset += 20

def stable_phase(
    seed: Any,
    hash_base: int = 31,
    scramble_shift1: int = 16,
    scramble_shift2: int = 3,
) -> float:
    """
    Generate a stable [0, 2π) phase offset from any hashable seed.
    Close seeds produce distinct but smooth phase values.
    
    Parameters:
        seed: any hashable value (str, int, tuple)
        hash_base: base multiplier for rolling hash
        scramble_shift1: first bitwise shift for scrambling
        scramble_shift2: second bitwise shift for scrambling
    
    Returns:
        Phase value in radians [0, 2π)
    """
    s = str(seed)
    
    v = 0
    for i, c in enumerate(s):
        v = (v * hash_base + ord(c) * (i + 1)) & 0xFFFFFFFF
    
    v ^= (v >> scramble_shift1)
    v ^= (v << scramble_shift2) & 0xFFFFFFFF
    
    phase = (v / 2**32) * (2 * math.pi)
    return phase

def floating_bounce(
    seed: Any,
    amplitude: float = 0.05,
    frequency: float = 1.0,
    time: float = 0.0,
) -> float:
    """
    Compute a gentle floating offset using a stable phase.
    
    Parameters:
        seed: any hashable value to generate a unique phase
        amplitude: max vertical displacement
        frequency: speed of the bounce (cycles per second)
        time: current time in seconds
    
    Returns:
        Vertical offset value
    """
    phase = stable_phase(seed, hash_base=31, scramble_shift1=16, scramble_shift2=3)
    offset = amplitude * math.sin(2 * math.pi * frequency * time + phase)
    return offset
