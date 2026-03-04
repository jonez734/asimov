import numpy as np
from collections import deque
from asimov import io
from asimov import conf
from asimov.base.common import ThreadSafeContext

# ------------------------------------------------------------
# Context key (ABI-STABLE)
# ------------------------------------------------------------

CTX_KEY = "MOTIONBLUR"

# ------------------------------------------------------------
# Detect phase (state update only)
# ------------------------------------------------------------

def detect(frame, context: ThreadSafeContext, **kwargs):
    try:
        # ---- Init ----------------------------------------------------------
        if CTX_KEY not in context:
            context[CTX_KEY] = {
                "frames": deque(maxlen=conf.MOTIONBLUR["HISTORY_LEN"]),
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

    except Exception:
        if CTX_KEY in context:
            context[CTX_KEY]["error_state"] = True
        io.echo_traceback("motionblur detect exception")


# ------------------------------------------------------------
# Draw phase (frame mutation)
# ------------------------------------------------------------

def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
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

    # ---- Blur strength ----------------------------------------------------
    alpha = np.clip(
        velocity / conf.MOTIONBLUR["VELOCITY_NORM"],
        conf.MOTIONBLUR["ALPHA_MIN"],
        conf.MOTIONBLUR["ALPHA_MAX"],
    )

    frames = ns["frames"]
    frames.append(frame.copy())

    if len(frames) < 2 or velocity < 1e-3:
        return frame

    # ---- Normalize direction ---------------------------------------------
    mag = max((dx * dx + dy * dy) ** 0.5, 1e-6)
    ux = dx / mag
    uy = dy / mag

    max_offset = conf.MOTIONBLUR["MAX_OFFSET"]
    total = len(frames)

    # ---- Base fingertip mask ---------------------------------------------
    h, w = frame.shape[:2]
###    radius = conf.MOTIONBLUR["RADIUS"]
    radius = int(np.clip(velocity * 0.4, 6, 24))

    yy, xx = np.ogrid[:h, :w]
    base_mask = (xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2
    base_mask = base_mask.astype(np.float32)[..., None]

    # ---- Optional yellow color gate --------------------------------------
    if conf.MOTIONBLUR.get("COLOR_GATE", False):
        import cv2
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lo = np.array(conf.MOTIONBLUR["YELLOW_MIN"], dtype=np.uint8)
        hi = np.array(conf.MOTIONBLUR["YELLOW_MAX"], dtype=np.uint8)
        color_mask = cv2.inRange(hsv, lo, hi).astype(np.float32) / 255.0
        color_mask = color_mask[..., None]
        mask = base_mask * color_mask
    else:
        mask = base_mask

    # ---- Directional accumulation ----------------------------------------
    blurred = np.zeros_like(frame, dtype=np.float32)

    weights = np.linspace(
        alpha,
        conf.MOTIONBLUR["TAIL_ALPHA"],
        total,
    )
    weights /= weights.sum()

    for i, (wgt, f) in enumerate(zip(weights, frames)):
        t = i / max(total - 1, 1)
        offset = int(t * max_offset)

        ox = int(-ux * offset)
        oy = int(-uy * offset)

        shifted = np.roll(f, shift=(oy, ox), axis=(0, 1))
        blurred += shifted.astype(np.float32) * wgt

    # ---- Composite --------------------------------------------------------
    frame[:] = (
        frame.astype(np.float32) * (1.0 - mask) +
        blurred * mask
    ).astype(np.uint8)

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


def main(args, **kwargs):
    return True
