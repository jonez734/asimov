import numpy as np
from collections import deque
from .. import io, conf
from ..base.common import ThreadSafeContext

# ------------------------------------------------------------
# Context key (ABI-STABLE)
# ------------------------------------------------------------

CTX_KEY = "MOTIONBLUR"

# ------------------------------------------------------------
# Detect phase (state update only)
# ------------------------------------------------------------


def detect(frame, context: ThreadSafeContext, **kwargs):
    confs = conf.CONF["MOTIONBLUR"]
    try:
        # ---- Init ----------------------------------------------------------
        if CTX_KEY not in context:
            context[CTX_KEY] = {
                "frames": deque(maxlen=confs["TRAIL"]["HISTORY_LEN"]),
                "last_pos": None,
                "active": False,
                "error_state": False,
            }

        ns = context[CTX_KEY]
        ns["active"] = False
        ns["error_state"] = False

        # ---- Consume INDEXFINGERTIP ---------------------------------------
        ft = context.get("INDEXFINGERTIP")
        if not ft or not ft.get("active"):
            ns["frames"].clear()
            ns["last_pos"] = None
            return

        data = ft.get("data")
        if not data:
            return

        x = data["x"]
        y = data["y"]

        # ---- Velocity ------------------------------------------------------
        last = ns["last_pos"]
        if last is None:
            dx = dy = 0.0
            velocity = 0.0
        else:
            dx = x - last[0]
            dy = y - last[1]
            velocity = (dx * dx + dy * dy) ** 0.5

        ns["last_pos"] = (x, y)
        ns["velocity"] = velocity
        ns["dx"] = dx
        ns["dy"] = dy
        ns["active"] = True

        # Capture frame with pointer position in detect phase to build history
        ns["frames"].append((frame.copy(), x, y))

    except Exception:
        if CTX_KEY in context:
            context[CTX_KEY]["error_state"] = True
        io.echo_traceback("motionblur detect exception")


# ------------------------------------------------------------
# Draw phase (frame mutation)
# ------------------------------------------------------------


def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    confs = conf.CONF["MOTIONBLUR"]
    ns = context.get(CTX_KEY)
    if not ns or ns.get("error_state") or not ns.get("active"):
        return frame

    ft = context.get("INDEXFINGERTIP")
    if not ft or not ft.get("active"):
        return frame

    data = ft.get("data")
    if not data:
        return frame

    x = int(data["x"])
    y = int(data["y"])

    velocity = ns.get("velocity", 0.0)
    dx = ns.get("dx", 0.0)
    dy = ns.get("dy", 0.0)

    mag = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    ux = 0.0
    uy = 0.0
    if mag >= 1e-6:
        ux = dx / mag
        uy = dy / mag

    alpha = np.clip(
        velocity / confs["VELOCITY"]["VELOCITY_NORM"],
        confs["ALPHA"]["ALPHA_MIN"],
        confs["ALPHA"]["ALPHA_MAX"],
    )

    frames = ns["frames"]

    if len(frames) < 2 or velocity < 1e-3:
        return frame

    frames_list = list(frames)

    h, w = frame.shape[:2]

    # Extract frames and stored positions from (frame, x, y) tuples
    frames_only = [item[0] for item in frames_list]
    positions = [(item[1], item[2]) for item in frames_list]

    oldest_frame = frames_only[0]
    newest_frame = frames_only[-1]

    if len(positions) < 2:
        return frame

    # Find bounding box of all stored pointer positions
    all_x = [p[0] for p in positions] + [x]
    all_y = [p[1] for p in positions] + [y]

    trail_min_x = min(all_x)
    trail_max_x = max(all_x)
    trail_min_y = min(all_y)
    trail_max_y = max(all_y)

    # Create circular masks at each position in the trail
    radius = confs["TRAIL"]["RADIUS"]
    yy, xx = np.ogrid[:h, :w]

    base_mask = np.zeros((h, w), dtype=np.float32)
    for px, py in positions:
        dist_sq = (xx - px) ** 2 + (yy - py) ** 2
        base_mask = np.maximum(base_mask, (dist_sq <= radius**2).astype(np.float32))

    # Add circle at current position
    dist_sq = (xx - x) ** 2 + (yy - y) ** 2
    base_mask = np.maximum(base_mask, (dist_sq <= radius**2).astype(np.float32))

    base_mask = base_mask[..., None]

    if confs["COLOR_GATE"].get("COLOR_GATE", False):
        import cv2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lo = np.array(confs["COLOR_GATE"]["YELLOW_MIN"], dtype=np.uint8)
        hi = np.array(confs["COLOR_GATE"]["YELLOW_MAX"], dtype=np.uint8)
        color_mask = cv2.inRange(hsv, lo, hi).astype(np.float32) / 255.0
        mask = base_mask * color_mask[..., None]
    else:
        mask = base_mask

    blurred = np.zeros_like(frame, dtype=np.float32)
    total = len(frames_only)

    weights = np.linspace(alpha, confs["ALPHA"]["TAIL_ALPHA"], total)
    weights /= weights.sum()

    max_offset = confs["TRAIL"]["MAX_OFFSET"]

    for i, (wgt, f) in enumerate(zip(weights, frames_only)):
        t = i / max(total - 1, 1)
        offset = int(t * max_offset)
        ox = int(-ux * offset)
        oy = int(-uy * offset)
        shifted = np.roll(f, shift=(oy, ox), axis=(0, 1))
        blurred += shifted.astype(np.float32) * wgt

    # Use newest stored frame as base (clean, no webcam noise)
    # Only apply trail in mask area, preserve original frame elsewhere
    base_frame = newest_frame.astype(np.float32)
    composite = (base_frame * (1.0 - mask) + blurred * mask).astype(np.uint8)

    frame[:] = composite
    return frame


# ------------------------------------------------------------
# Required lifecycle hooks
# ------------------------------------------------------------


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def get_stateful_keys() -> list[str]:
    """Return list of context keys this module manages."""
    return ["MOTIONBLUR"]


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "TRAIL": {
            "HISTORY_LEN": {
                "type": "int",
                "default": 8,
                "min": 2,
                "max": 30,
                "step": 1,
                "label": "History Length",
            },
            "RADIUS": {
                "type": "int",
                "default": 6,
                "min": 1,
                "max": 50,
                "step": 1,
                "label": "Trail Radius",
            },
            "MAX_OFFSET": {
                "type": "int",
                "default": 20,
                "min": 1,
                "max": 100,
                "step": 1,
                "label": "Max Offset",
            },
        },
        "ALPHA": {
            "ALPHA_MIN": {
                "type": "float",
                "default": 0.15,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Alpha Min",
            },
            "ALPHA_MAX": {
                "type": "float",
                "default": 0.85,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Alpha Max",
            },
            "TAIL_ALPHA": {
                "type": "float",
                "default": 0.05,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "label": "Tail Alpha",
            },
        },
        "VELOCITY": {
            "VELOCITY_NORM": {
                "type": "float",
                "default": 40.0,
                "min": 1.0,
                "max": 200.0,
                "step": 1.0,
                "label": "Velocity Normalization",
            },
            "RADIUS_VELOCITY_NORM": {
                "type": "float",
                "default": 40.0,
                "min": 1.0,
                "max": 200.0,
                "step": 1.0,
                "label": "Radius Velocity Norm",
            },
        },
        "COLOR_GATE": {
            "COLOR_GATE": {
                "type": "bool",
                "default": True,
                "label": "Enable Color Gate",
            },
            "RADIUS_MIN_FRAC": {
                "type": "float",
                "default": 0.006,
                "min": 0.001,
                "max": 0.1,
                "step": 0.001,
                "label": "Radius Min Fraction",
            },
            "RADIUS_MAX_FRAC": {
                "type": "float",
                "default": 0.025,
                "min": 0.001,
                "max": 0.1,
                "step": 0.001,
                "label": "Radius Max Fraction",
            },
        },
    }


def main(args, **kwargs):
    return True
