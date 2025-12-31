# asimov/eyes.py
import cv2
import numpy as np
import time
from cvzone.FaceMeshModule import FaceMeshDetector

from . import io, conf
from .common import ThreadSafeContext, OneEuroFilter

# --- Internal helpers ---

def _draw_rotated_bar(img, center, size, angle_deg, color, alpha):
    """Draws a rotated rectangle (privacy bar) with alpha blending."""
    rect = ((center[0], center[1]), (size[0], size[1]), angle_deg)
    box = cv2.boxPoints(rect).astype(int)

    overlay = img.copy()
    cv2.fillConvexPoly(overlay, box, color)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

# --- Module methods ---

def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    """Detect eyes using cvzone and update namespaced context."""
    
    # Namespaced initialization
    if "EYES" not in context:
        f_params = conf.EYES["FILTER"]
        context["EYES"] = {
            "detector": FaceMeshDetector(
                staticMode=False,
                maxFaces=conf.EYES["FACE_MESH"]["MAX_FACES"],
                minDetectionCon=conf.EYES["FACE_MESH"]["DETECTION_CON"],
                minTrackCon=conf.EYES["FACE_MESH"]["TRACKING_CON"]
            ),
            "ema": {
                key: OneEuroFilter(freq=f_params["FREQ"], min_cutoff=f_params["MIN_CUTOFF"], beta=f_params["BETA"])
                for key in ["cx", "cy", "w", "h", "angle"]
            },
            "data": None
        }

    ns = context["EYES"]
    detector = ns["detector"]
    
    # Use config for internal drawing
    _, faces = detector.findFaceMesh(frame, draw=conf.EYES.get("DRAW_DETECTION", False))
    
    bar = ns["data"]

    if faces:
        face = faces[0]
        l_idx = conf.EYES["INDICES"]["LEFT_EYE"]
        r_idx = conf.EYES["INDICES"]["RIGHT_EYE"]
        
        left_pts = np.array([face[i] for i in l_idx])
        right_pts = np.array([face[i] for i in r_idx])
        all_eye_pts = np.vstack((left_pts, right_pts))
        
        left_center = np.mean(left_pts, axis=0)
        right_center = np.mean(right_pts, axis=0)
        min_coords = np.min(all_eye_pts, axis=0)
        max_coords = np.max(all_eye_pts, axis=0)
        
        raw_w = max_coords[0] - min_coords[0]
        raw_h = max_coords[1] - min_coords[1]
        cx, cy = (min_coords[0] + max_coords[0]) / 2, (min_coords[1] + max_coords[1]) / 2

        delta = right_center - left_center
        angle = np.degrees(np.arctan2(delta[1], delta[0]))

        ema = ns["ema"]
        bar = {
            "cx": ema["cx"].update(cx),
            "cy": ema["cy"].update(cy),
            "w":  ema["w"].update(raw_w * conf.EYES["BAR"]["WIDTH_SCALE"]),
            "h":  ema["h"].update(raw_h * conf.EYES["BAR"]["HEIGHT_SCALE"]),
            "angle": ema["angle"].update(angle),
            "timestamp": time.time(),
        }
    
    elif bar and (time.time() - bar["timestamp"] < conf.EYES["BAR"]["GRACE_PERIOD"]):
        pass
    else:
        bar = None

    ns["data"] = bar

def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    """Draw the privacy bar using namespaced context data."""
    ns = context.get("EYES")
    if not ns or not ns.get("data"):
        return frame

    bar = ns["data"]
    _draw_rotated_bar(
        frame, 
        (int(bar["cx"]), int(bar["cy"])), 
        (int(bar["w"]), int(bar["h"])), 
        bar["angle"],
        color=conf.EYES["BAR"]["COLOR"], 
        alpha=conf.EYES["BAR"]["ALPHA"]
    )
    return frame

def main(args, **kwargs):
###    io.echo("eyes_next: namespaced robust mode active")
    return True

def init(args, **kwargs):
    return True

def access(args, op, /, **kwargs):
    return True

def buildargs(args, **kwargs):
    return None
