from OpenGL.GL import *
from OpenGL.GLUT import *

from math import log2, ceil
import struct
from dataclasses import dataclass, field

import numpy as np

import cv2

MAX_BLOCK_SIZE = 128

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


import cv2
import numpy as np

def draw_text(img, x, y, text,
              color=(255, 255, 255), alpha=1.0,
              shadow_offset=1, shadow_color=(0, 0, 0), shadow_alpha=1.0,
              thickness=1, font_scale=0.5,
              font=cv2.FONT_HERSHEY_SIMPLEX):
    """
    Draw text with a shadow effect on an image using OpenCV with alpha blending.

    Parameters:
        img (np.ndarray): Image to draw on (BGR or BGRA).
        x, y (int): Coordinates of the text baseline.
        text (str): Text string to draw.
        color (tuple): Text color (B, G, R).
        alpha (float): Opacity of main text (0.0 to 1.0).
        shadow_offset (int): Offset for the shadow in pixels.
        shadow_color (tuple): Shadow color (B, G, R).
        shadow_alpha (float): Opacity of shadow (0.0 to 1.0).
        thickness (int): Thickness of the text stroke.
        font_scale (float): Scale factor for the text size.
        font (int): OpenCV font type.
    """
    overlay = img.copy()

    # Draw shadow
    cv2.putText(overlay, text, (x + shadow_offset, y + shadow_offset),
                font, font_scale, shadow_color, thickness, cv2.LINE_AA)
    img[:] = cv2.addWeighted(overlay, shadow_alpha, img, 1 - shadow_alpha, 0)

    # Draw main text
    overlay = img.copy()
    cv2.putText(overlay, text, (x, y),
                font, font_scale, color, thickness, cv2.LINE_AA)
    img[:] = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

    return img
