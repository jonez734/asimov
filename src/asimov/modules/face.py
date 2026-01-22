# asimov/face.py
import time
import numpy as np
from cvzone.FaceMeshModule import FaceMeshDetector

from . import conf
from .common import ThreadSafeContext

# Context namespace key
_NS = "FACE"

def detect(frame: np.ndarray, context: ThreadSafeContext, **kwargs):
    """
    FaceMesh detection module.
    Publishes raw face landmarks into context["FACE"].
    """

    # Lazy init
    if _NS not in context:
        fm_conf = conf.FACE["MESH"]
        context[_NS] = {
            "detector": FaceMeshDetector(
                staticMode=False,
                maxFaces=fm_conf["MAX_FACES"],
                minDetectionCon=fm_conf["DETECTION_CON"],
                minTrackCon=fm_conf["TRACKING_CON"],
            ),
            "faces": None,
            "timestamp": 0.0,
        }

    ns = context[_NS]
    detector = ns["detector"]

    _, faces = detector.findFaceMesh(
        frame,
        draw=conf.EYES.get("DRAW_DETECTION", False),
    )

    if faces:
        ns["faces"] = faces
        ns["timestamp"] = time.time()
    else:
        ns["faces"] = None

def draw(frame: np.ndarray, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    """
    Face module does not draw anything itself.
    """
    return frame

def main(args, **kwargs) -> bool:
    return True

def init(args, **kwargs) -> bool:
    return True

def access(args, op, /, **kwargs) -> bool:
    return True

def buildargs(args, **kwargs):
    return None
