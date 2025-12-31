# asimov/indexfingertip.py

import cv2
import numpy as np
import time
from cvzone.HandTrackingModule import HandDetector
from . import io, conf, module
from .common import ThreadSafeContext, OneEuroFilter

# Constants
INDEX_FINGER_TIP_LM = 8
INDEX_UP_PATTERN = [0, 1, 0, 0, 0]
ERR_TEXT_ORG = (10, 30)
ERR_TEXT_SCALE = 0.6
ERR_TEXT_THICKNESS = 2

def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
###    io.echo("asimov.indexfingertip.detect.100: trace", level="debug")
    try:
        # Resource Initialization
        if "FINGERTIP" not in context:
            io.echo("Initializing Fingertip Detector resources...", level="info")
            f_params = conf.FINGERTIP["FILTER"]
            # Store in context under a namespace
            context["FINGERTIP"] = {
                "detector": HandDetector(
                    detectionCon=conf.FINGERTIP.get("DETECTION_CON", 0.8),
                    maxHands=conf.FINGERTIP.get("MAX_HANDS", 1)
                ),
                "ema": {
                    "x": OneEuroFilter(freq=f_params["FREQ"], min_cutoff=f_params["MIN_CUTOFF"], beta=f_params["BETA"]),
                    "y": OneEuroFilter(freq=f_params["FREQ"], min_cutoff=f_params["MIN_CUTOFF"], beta=f_params["BETA"])
                },
                "data": None,
                "error_state": False
            }

        ns = context["FINGERTIP"]
        ns["error_state"] = False # Reset error state on new attempt

        hands, frame = ns["detector"].findHands(frame, draw=True)

        if hands:
            hand = hands[0]
            if ns["detector"].fingersUp(hand) == INDEX_UP_PATTERN:
                raw_x, raw_y = hand['lmList'][INDEX_FINGER_TIP_LM][:2]
                ns["data"] = {
                    "x": ns["ema"]["x"].update(raw_x),
                    "y": ns["ema"]["y"].update(raw_y),
                    "timestamp": time.time(),
                }
                # Update context to ensure thread visibility
                context["FINGERTIP"] = ns
                return

        # Check grace period for data persistence
        if ns["data"]:
            if (time.time() - ns["data"]["timestamp"] > conf.FINGERTIP.get("GRACE_PERIOD", 0.5)):
                ns["data"] = None

        context["FINGERTIP"] = ns

    except Exception:
        if "FINGERTIP" in context:
            context["FINGERTIP"]["error_state"] = True
        io.echo_traceback("Fingertip logic exception")

def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    ns = context.get("FINGERTIP")
    if not ns:
        return frame

    if ns.get("error_state"):
        cv2.putText(frame, "FINGERTIP ERROR", ERR_TEXT_ORG,
                    cv2.FONT_HERSHEY_SIMPLEX, ERR_TEXT_SCALE, (0, 0, 255), ERR_TEXT_THICKNESS)
        return frame

    try:
        data = ns.get("data")
        if data:
            cv2.circle(
                frame,
                (int(data["x"]), int(data["y"])),
                conf.FINGERTIP.get("CIRCLE_RADIUS", 10),
                conf.FINGERTIP.get("COLOR", (0, 255, 0)),
                cv2.FILLED
            )
        return frame
    except Exception:
        io.echo_traceback("Fingertip draw exception")
        return frame # Return original frame instead of None to prevent flickering

def init(args, **kwargs):
###    io.echo("asimov.indexfingertip.init.100: trace", level="debug")
    return True

def buildargs(args, **kwargs):
    return None

def access(args, op, /, **kwargs):
    return True

def main(args, **kwargs):
    # This acts as the lifecycle 'run' entry point for indexfingertip

    return True
