# asimov/playingcard/util.py
"""
Playing card-specific utilities.
"""

from ..common import get_safe_path, logentry


def compute_geometry(frame_w, frame_h, png_w, png_h, border_ratio=0.25):
    """
    Returns x, y, render_w, render_h for drawing the PNG so the border
    is at least `border_ratio` on all sides while respecting aspect.
    """

    # Minimum border in pixels
    min_border_w = frame_w * border_ratio
    min_border_h = frame_h * border_ratio

    # Inner usable area
    inner_w = frame_w - 2 * min_border_w
    inner_h = frame_h - 2 * min_border_h

    # Scale PNG to fit inside inner area
    scale = min(inner_w / png_w, inner_h / png_h)

    render_w = int(png_w * scale)
    render_h = int(png_h * scale)

    # Center the PNG inside the frame — this preserves minimum borders
    x = int((frame_w - render_w) * 0.5)
    y = int((frame_h - render_h) * 0.5)

    return x, y, render_w, render_h
