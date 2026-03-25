# asimov/modules/face.py
import time
import cv2
from cvzone.FaceMeshModule import FaceMeshDetector
from .. import conf, io
from ..base.common import ThreadSafeContext
from ..base.util import draw_text
from . import mediapipe_compat  # noqa: F401  # REQUIRED - do not remove; provides mp.solutions API for MediaPipe 0.10+
import numpy as np

_FACE_OVAL = frozenset(
    [
        (10, 338),
        (338, 297),
        (297, 332),
        (332, 284),
        (284, 251),
        (251, 389),
        (389, 356),
        (356, 454),
        (454, 323),
        (323, 361),
        (361, 288),
        (288, 397),
        (397, 365),
        (365, 379),
        (379, 378),
        (378, 400),
        (400, 377),
        (377, 152),
        (152, 148),
        (148, 176),
        (176, 149),
        (149, 150),
        (150, 136),
        (136, 172),
        (172, 58),
        (58, 132),
        (132, 93),
        (93, 234),
        (234, 127),
        (127, 162),
        (162, 21),
        (21, 54),
        (54, 103),
        (103, 104),
        (104, 33),
        (33, 7),
        (7, 163),
        (163, 144),
        (144, 145),
        (145, 153),
        (153, 154),
        (154, 155),
        (155, 133),
        (133, 246),
        (246, 161),
        (161, 160),
        (160, 159),
        (159, 158),
        (158, 157),
        (157, 173),
        (173, 133),
    ]
)

_LIPS = frozenset(
    [
        (61, 146),
        (146, 91),
        (91, 181),
        (181, 84),
        (84, 17),
        (17, 314),
        (314, 405),
        (405, 321),
        (321, 375),
        (375, 291),
        (61, 185),
        (185, 40),
        (40, 39),
        (39, 37),
        (37, 0),
        (0, 267),
        (267, 269),
        (269, 270),
        (270, 409),
        (409, 291),
        (78, 95),
        (95, 88),
        (88, 178),
        (178, 87),
        (87, 14),
        (14, 317),
        (317, 402),
        (402, 318),
        (318, 324),
        (324, 308),
        (78, 191),
        (191, 80),
        (80, 81),
        (81, 82),
        (82, 13),
        (13, 312),
        (312, 311),
        (311, 310),
        (310, 415),
        (415, 308),
    ]
)

_LEFT_EYEBROW = frozenset(
    [
        (276, 283),
        (283, 282),
        (282, 295),
        (295, 285),
        (285, 295),
        (300, 29),
        (29, 56),
        (56, 157),
        (157, 154),
        (154, 153),
        (153, 145),
        (145, 144),
        (70, 63),
        (63, 105),
        (105, 66),
        (66, 107),
    ]
)

_RIGHT_EYEBROW = frozenset(
    [
        (46, 53),
        (53, 52),
        (52, 65),
        (65, 55),
        (55, 70),
        (334, 293),
        (293, 295),
        (295, 282),
        (282, 283),
        (283, 276),
        (276, 246),
        (246, 161),
    ]
)

_LEFT_EYE = frozenset(
    [
        (263, 249),
        (249, 390),
        (390, 373),
        (373, 374),
        (374, 380),
        (380, 381),
        (381, 382),
        (382, 362),
        (263, 466),
        (466, 388),
        (388, 387),
        (387, 386),
        (386, 385),
        (385, 384),
        (384, 398),
        (398, 362),
    ]
)

_RIGHT_EYE = frozenset(
    [
        (33, 7),
        (7, 163),
        (163, 144),
        (144, 145),
        (145, 153),
        (153, 154),
        (154, 155),
        (155, 133),
        (33, 246),
        (246, 161),
        (161, 160),
        (160, 159),
        (159, 158),
        (158, 157),
        (157, 173),
        (173, 133),
    ]
)

_LEFT_IRIS = frozenset(
    [
        (474, 475),
        (475, 476),
        (476, 477),
        (477, 474),
    ]
)

_RIGHT_IRIS = frozenset(
    [
        (469, 470),
        (470, 471),
        (471, 472),
        (472, 469),
    ]
)

_NOSE = frozenset(
    [
        (168, 6),
        (6, 197),
        (197, 195),
        (195, 5),
        (5, 4),
        (4, 45),
        (45, 275),
        (275, 440),
        (440, 344),
        (344, 278),
        (278, 279),
        (279, 288),
        (288, 361),
        (361, 323),
        (323, 454),
        (454, 356),
        (356, 389),
        (389, 251),
        (251, 284),
    ]
)

_TESSELATION = frozenset(
    [
        (127, 34),
        (34, 139),
        (139, 127),
        (11, 0),
        (0, 37),
        (37, 11),
        (232, 231),
        (231, 120),
        (120, 232),
        (11, 172),
        (172, 58),
        (58, 132),
        (132, 93),
        (93, 234),
        (234, 127),
        (11, 73),
        (73, 74),
        (74, 61),
        (61, 146),
        (146, 91),
        (91, 181),
        (181, 84),
        (84, 17),
        (17, 314),
        (314, 405),
        (405, 321),
        (321, 375),
        (375, 291),
        (11, 37),
        (37, 0),
        (0, 267),
        (267, 269),
        (269, 270),
        (270, 409),
        (409, 291),
        (11, 195),
        (195, 5),
        (5, 4),
        (4, 45),
        (45, 275),
        (275, 440),
        (440, 344),
        (344, 278),
        (278, 279),
        (279, 288),
        (288, 361),
        (361, 323),
        (323, 454),
        (454, 356),
        (356, 389),
        (389, 251),
        (251, 284),
        (284, 332),
        (332, 297),
        (297, 338),
        (338, 10),
        (11, 165),
        (165, 92),
        (92, 165),
        (11, 365),
        (365, 379),
        (379, 378),
        (378, 400),
        (400, 377),
        (377, 152),
        (152, 148),
        (148, 176),
        (176, 149),
        (149, 150),
        (150, 136),
        (136, 172),
        (11, 43),
        (43, 106),
        (106, 196),
        (196, 195),
        (11, 255),
        (255, 359),
        (359, 255),
        (11, 1),
        (1, 38),
        (38, 39),
        (39, 40),
        (40, 185),
        (185, 170),
        (170, 140),
        (140, 171),
        (171, 175),
        (175, 396),
        (396, 369),
        (369, 395),
        (395, 394),
        (11, 15),
        (15, 86),
        (86, 85),
        (85, 16),
        (16, 68),
        (68, 71),
        (71, 67),
        (67, 54),
        (54, 21),
        (21, 162),
        (162, 54),
        (11, 247),
        (247, 201),
        (201, 200),
        (200, 199),
        (199, 175),
        (175, 396),
        (11, 338),
        (338, 297),
        (297, 332),
        (332, 284),
        (284, 251),
        (251, 389),
        (389, 356),
        (356, 454),
        (454, 323),
        (323, 361),
        (361, 288),
        (288, 397),
        (397, 365),
        (365, 379),
        (379, 378),
        (378, 400),
        (400, 377),
        (377, 152),
        (152, 148),
        (148, 176),
        (176, 149),
        (149, 150),
        (150, 136),
        (136, 172),
        (172, 58),
        (58, 132),
        (132, 93),
        (93, 234),
        (234, 127),
        (127, 162),
        (162, 21),
        (21, 54),
        (54, 103),
        (103, 104),
        (104, 33),
        (33, 7),
        (7, 163),
        (163, 144),
        (144, 145),
        (145, 153),
        (153, 154),
        (154, 155),
        (155, 133),
        (133, 246),
        (246, 161),
        (161, 160),
        (160, 159),
        (159, 158),
        (158, 157),
        (157, 173),
        (173, 133),
        (11, 226),
        (226, 31),
        (31, 189),
        (189, 242),
        (242, 46),
        (46, 114),
        (114, 188),
        (188, 95),
        (95, 80),
        (80, 81),
        (81, 82),
        (82, 13),
        (13, 311),
        (311, 402),
        (402, 318),
        (318, 324),
        (324, 308),
        (11, 129),
        (129, 98),
        (98, 97),
        (97, 99),
        (99, 100),
        (100, 47),
        (47, 115),
        (115, 48),
        (48, 59),
        (59, 60),
        (60, 305),
        (305, 275),
        (275, 440),
        (440, 344),
        (344, 78),
        (78, 95),
        (95, 88),
        (88, 178),
        (178, 87),
        (87, 14),
        (14, 317),
        (317, 402),
        (402, 318),
        (318, 324),
        (324, 308),
        (11, 156),
        (156, 70),
        (70, 63),
        (63, 105),
        (105, 66),
        (66, 107),
        (107, 55),
        (55, 46),
        (46, 124),
        (124, 110),
        (110, 65),
        (65, 52),
        (52, 53),
        (53, 46),
        (11, 53),
        (53, 52),
        (52, 65),
        (65, 55),
        (55, 107),
        (107, 66),
        (66, 105),
        (105, 63),
        (63, 70),
        (70, 156),
        (156, 124),
        (124, 110),
        (110, 109),
        (11, 10),
        (10, 109),
        (109, 110),
        (110, 124),
        (124, 156),
        (156, 70),
        (70, 63),
        (63, 105),
        (105, 66),
        (66, 107),
        (107, 55),
        (55, 65),
        (65, 52),
        (52, 53),
        (53, 46),
        (46, 53),
    ]
)


def _get_connections(mode: str, draw_iris: bool) -> frozenset:
    connections = set()
    if mode == "key":
        connections.update(_FACE_OVAL)
        connections.update(_LIPS)
        connections.update(_LEFT_EYE)
        connections.update(_RIGHT_EYE)
        connections.update(_LEFT_EYEBROW)
        connections.update(_RIGHT_EYEBROW)
        connections.update(_NOSE)
        if draw_iris:
            connections.update(_LEFT_IRIS)
            connections.update(_RIGHT_IRIS)
    else:
        connections.update(_TESSELATION)
    return frozenset(connections)


def detect(frame, context: ThreadSafeContext, **kwargs):
    try:
        if "FACE" not in context:
            cfg = conf.get("FACE")
            if "MESH" in cfg:
                cfg["MAX_FACES"] = cfg["MESH"].get("MAX_FACES", 1)
                cfg["DETECTION_CON"] = cfg["MESH"].get("DETECTION_CON", 0.5)
                cfg["TRACKING_CON"] = cfg["MESH"].get("TRACKING_CON", 0.5)
            if "OUTPUT" in cfg:
                cfg["LANDMARKS"] = cfg["OUTPUT"].get("LANDMARKS", True)
                cfg["GRACE_PERIOD"] = cfg["OUTPUT"].get("GRACE_PERIOD", 0.35)
            cfg["DRAW_DETECTION"] = cfg.get("DRAW", {}).get("DETECTION", False)

            context["FACE"] = {
                "cfg": cfg,
                "detector": FaceMeshDetector(
                    maxFaces=cfg.get("MAX_FACES", 1),
                    minDetectionCon=cfg.get("DETECTION_CON", 0.5),
                    minTrackCon=cfg.get("TRACKING_CON", 0.5),
                ),
                "faces": None,
                "timestamp": None,
                "error_state": False,
            }

        ns = context["FACE"]
        ns["error_state"] = False

        cfg = conf.get("FACE")
        if "MESH" in cfg:
            cfg["MAX_FACES"] = cfg["MESH"].get("MAX_FACES", 1)
            cfg["DETECTION_CON"] = cfg["MESH"].get("DETECTION_CON", 0.5)
            cfg["TRACKING_CON"] = cfg["MESH"].get("TRACKING_CON", 0.5)
        if "OUTPUT" in cfg:
            cfg["LANDMARKS"] = cfg["OUTPUT"].get("LANDMARKS", True)
            cfg["GRACE_PERIOD"] = cfg["OUTPUT"].get("GRACE_PERIOD", 0.35)
        cfg["DRAW_DETECTION"] = cfg.get("DRAW", {}).get("DETECTION", False)
        ns["cfg"] = cfg

        detector = ns["detector"]

        _, faces = detector.findFaceMesh(frame, draw=False)

        if faces:
            normalized_faces = []
            for face in faces:
                landmarks = face[1:]
                normalized = []
                for lm in landmarks:
                    normalized.append((lm[0], lm[1], lm[2] if len(lm) > 2 else 0.0))
                normalized_faces.append(normalized)
            ns["faces"] = normalized_faces
        else:
            ns["faces"] = None

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
        frame = draw_text(
            frame, 10, 30, "FACE ERROR", color=(0, 0, 255), font_scale=0.6, thickness=2
        )
        return frame

    cfg = ns.get("cfg", {})
    draw_cfg = cfg.get("DRAW", {})

    if not draw_cfg.get("DETECTION", False):
        return frame

    faces = ns.get("faces")
    if not faces:
        return frame

    try:
        mode = str(draw_cfg.get("MODE", "key"))
        draw_iris = bool(draw_cfg.get("DRAW_IRIS", False))
        mirror = bool(draw_cfg.get("MIRROR", False))
        alpha = float(draw_cfg.get("ALPHA", 1.0))
        color = draw_cfg.get("COLOR", (0, 255, 0))
        line_thickness = int(draw_cfg.get("LINE_THICKNESS", 1))
        point_radius = int(draw_cfg.get("POINT_RADIUS", 1))
    except (TypeError, ValueError):
        mode = "key"
        draw_iris = False
        mirror = False
        alpha = 1.0
        color = (0, 255, 0)
        line_thickness = 1
        point_radius = 1

    if alpha is None or not isinstance(alpha, (int, float)) or alpha < 0.0 or alpha > 1.0:
        alpha = 1.0

    if not isinstance(color, tuple) or len(color) != 3:
        color = (0, 255, 0)

    line_thickness = max(1, min(5, line_thickness))
    point_radius = max(0, min(5, point_radius))

    connections = _get_connections(mode, draw_iris)

    working_frame = frame.copy()
    if mirror:
        working_frame = cv2.flip(working_frame, 1)

    for face in faces:
        for start_idx, end_idx in connections:
            if start_idx < len(face) and end_idx < len(face):
                pt1 = (int(face[start_idx][0]), int(face[start_idx][1]))
                pt2 = (int(face[end_idx][0]), int(face[end_idx][1]))
                cv2.line(working_frame, pt1, pt2, color, line_thickness)

        if point_radius > 0:
            for lm in face:
                pt = (int(lm[0]), int(lm[1]))
                cv2.circle(working_frame, pt, point_radius, color, -1)

    if mirror:
        working_frame = cv2.flip(working_frame, 1)

    if alpha < 1.0:
        frame = cv2.addWeighted(working_frame, alpha, frame, 1 - alpha, 0)
    else:
        frame = working_frame

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
                "label": "Maximum Faces",
            },
            "DETECTION_CON": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Detection Confidence",
            },
            "TRACKING_CON": {
                "type": "float",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "label": "Tracking Confidence",
            },
        },
        "OUTPUT": {
            "GRACE_PERIOD": {
                "type": "float",
                "default": 0.35,
                "min": 0.0,
                "max": 2.0,
                "step": 0.05,
                "label": "Grace Period (seconds)",
            }
        },
        "DRAW": {
            "DETECTION": {"type": "bool", "default": False, "label": "Draw Face Mesh"},
            "MODE": {
                "type": "enum",
                "default": "key",
                "options": [("key", "Key Features"), ("all", "All Landmarks")],
                "label": "Landmark Mode",
            },
            "DRAW_IRIS": {"type": "bool", "default": False, "label": "Draw Irises"},
            "MIRROR": {"type": "bool", "default": True, "label": "Mirror Frame"},
            "ALPHA": {
                "type": "float",
                "default": 1.0,
                "min": 0.1,
                "max": 1.0,
                "step": 0.1,
                "label": "Opacity",
            },
            "COLOR": {"type": "color", "default": (0, 255, 0), "label": "Color"},
            "LINE_THICKNESS": {
                "type": "int",
                "default": 1,
                "min": 1,
                "max": 5,
                "step": 1,
                "label": "Line Thickness",
            },
            "POINT_RADIUS": {
                "type": "int",
                "default": 1,
                "min": 1,
                "max": 5,
                "step": 1,
                "label": "Point Radius",
            },
        },
    }


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
