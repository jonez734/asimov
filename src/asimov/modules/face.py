# asimov/modules/face.py
import time
import cv2
import mediapipe_compat
import mediapipe as mp
from asimov import io
from asimov import conf
from asimov.base.common import ThreadSafeContext
import numpy as np


def detect(frame, context: ThreadSafeContext, **kwargs):
    try:
        if "FACE" not in context:
            cfg = conf.FACE.copy()
            if "MESH" in cfg:
                cfg["MAX_FACES"] = cfg["MESH"].get("MAX_FACES", 1)
                cfg["DETECTION_CON"] = cfg["MESH"].get("DETECTION_CON", 0.5)
                cfg["TRACKING_CON"] = cfg["MESH"].get("TRACKING_CON", 0.5)
            if "OUTPUT" in cfg:
                cfg["LANDMARKS"] = cfg["OUTPUT"].get("LANDMARKS", True)
                cfg["GRACE_PERIOD"] = cfg["OUTPUT"].get("GRACE_PERIOD", 0.35)
            cfg["DRAW_DETECTION"] = cfg.get("DRAW_DETECTION", False)

            context["FACE"] = {
                "cfg": cfg,
                "detector": mp.solutions.face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=cfg.get("MAX_FACES", 1),
                    refine_landmarks=False,
                    min_detection_confidence=cfg.get("DETECTION_CON", 0.5),
                    min_tracking_confidence=cfg.get("TRACKING_CON", 0.5),
                ),
                "faces": None,
                "timestamp": None,
                "error_state": False,
            }

        ns = context["FACE"]
        ns["error_state"] = False

        cfg = conf.FACE.copy()
        if "MESH" in cfg:
            cfg["MAX_FACES"] = cfg["MESH"].get("MAX_FACES", 1)
            cfg["DETECTION_CON"] = cfg["MESH"].get("DETECTION_CON", 0.5)
            cfg["TRACKING_CON"] = cfg["MESH"].get("TRACKING_CON", 0.5)
        if "OUTPUT" in cfg:
            cfg["LANDMARKS"] = cfg["OUTPUT"].get("LANDMARKS", True)
            cfg["GRACE_PERIOD"] = cfg["OUTPUT"].get("GRACE_PERIOD", 0.35)
        cfg["DRAW_DETECTION"] = cfg.get("DRAW_DETECTION", False)
        ns["cfg"] = cfg

        detector = ns["detector"]

        results = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        faces = []
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                face = []
                for lm in face_landmarks.landmark:
                    h, w = frame.shape[:2]
                    face.append((lm.x * w, lm.y * h, lm.z * w))
                faces.append(face)

        ns["faces"] = faces if faces else None
        ns["timestamp"] = time.time()

        context["FACE"] = ns

    except Exception:
        if "FACE" in context:
            context["FACE"]["error_state"] = True
        io.echo_traceback("Face detection exception")


def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    ns = context.get("FACE")
    if not ns:
        return frame

    if ns.get("error_state"):
        cv2.putText(frame, "FACE ERROR", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return frame

    return frame


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "MESH": {
            "MAX_FACES": {
                "type": "int",
                "default": 1,
                "min": 1,
                "max": 4,
                "step": 1,
                "label": "Maximum Faces"
            },
            "DETECTION_CON": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Detection Confidence"
            },
            "TRACKING_CON": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Tracking Confidence"
            }
        },
        "OUTPUT": {
            "GRACE_PERIOD": {
                "type": "float",
                "default": 0.35,
                "min": 0.0,
                "max": 2.0,
                "step": 0.05,
                "label": "Grace Period (seconds)"
            }
        },
        "DRAW_DETECTION": {
            "type": "bool",
            "default": False,
            "label": "Draw Face Mesh"
        }
    }


def initgui(args, root) -> bool:
    return True


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
