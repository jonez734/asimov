import os
from ..common import logentry

# @since 20251118 copied from bbsengine6.util
def get_safe_path(*components, **kwargs):
    """
    Constructs a safe path by joining multiple path components.
    Expands environment variables and user home director and normalizes
    """
    if not components:
        raise ValueError("At least one path component must be provided.")

    # Expand environment variables and `~` in all components
    components = [os.path.expandvars(os.path.expanduser(component)) for component in components]

    # Join all components
    joined_path = os.path.join(*components)

    # Normalize the resulting path
    safe_path = os.path.normpath(joined_path)

    # Ensure the resulting path is absolute
    base_dir = os.path.abspath(components[0])
    if not safe_path.startswith(base_dir):
        raise ValueError("Invalid path: directory traversal detected.")

#    # Ensure the file exists
#    if not os.path.isfile(safe_path):
#        raise FileNotFoundError(f"File not found: {safe_path}")

    return safe_path

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

    render_w = png_w * scale
    render_h = png_h * scale

    # Center the PNG inside the frame — this preserves minimum borders
    x = (frame_w - render_w) * 0.5
    y = (frame_h - render_h) * 0.5
    
    logentry(f"asimov.playingcard.util.compute_geometry.100: {x=} {y=}")

    return int(x), int(y), int(render_w), int(render_h)
