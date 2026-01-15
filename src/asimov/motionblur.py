import numpy as np
from collections import deque
from . import conf, io
from .common import ThreadSafeContext

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
            velocity = 0.0
        else:
            dx = x - last[0]
            dy = y - last[1]
            velocity = (dx * dx + dy * dy) ** 0.5

        ns["last_pos"] = (x, y)
        ns["velocity"] = velocity
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
    if not ns:
        return frame

    if ns.get("error_state"):
        return frame

    if not ns.get("active"):
        return frame

    velocity = ns.get("velocity", 0.0)

    # ---- Blur strength ----------------------------------------------------
    alpha = np.clip(
        velocity / conf.MOTIONBLUR["VELOCITY_NORM"],
        conf.MOTIONBLUR["ALPHA_MIN"],
        conf.MOTIONBLUR["ALPHA_MAX"],
    )

    frames = ns["frames"]
    frames.append(frame.copy())

##    if len(frames) < 2:
##        return frame

    frames_snapshot = list(frames)
    
    out = np.zeros_like(frame, dtype=np.float32)

    weights = np.linspace(
        alpha,
        conf.MOTIONBLUR["TAIL_ALPHA"],
        len(frames),
    )
    weights /= weights.sum()

    for w, f in zip(weights, frames_snapshot):
        out += f.astype(np.float32) * w

    frame[:] = out.astype(np.uint8)
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
