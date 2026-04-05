# facemask.py
import os
import time
import cv2
import numpy as np
from .. import conf, io
from ..base.common import ThreadSafeContext

REQUIRES = {"FACE"}
PROVIDES = {"FACEMASK"}

_POSITION_LANDMARKS = {
    "TL": 234,
    "TC": 10,
    "TR": 454,
}


def _get_face_bbox(landmarks):
    if not landmarks:
        return None
    xs = [p[0] for p in landmarks]
    ys = [p[1] for p in landmarks]
    return (min(xs), min(ys), max(xs), max(ys))


def _get_landmark_coords(landmarks, idx):
    if idx is None or idx >= len(landmarks):
        return None
    return (int(landmarks[idx][0]), int(landmarks[idx][1]))


def _overlay_png(bg, overlay, x, y, scale=1.0):
    if overlay is None:
        return bg

    h, w = overlay.shape[:2]
    new_w = int(w * scale)
    new_h = int(h * scale)

    if new_w <= 0 or new_h <= 0:
        return bg

    overlay_resized = cv2.resize(overlay, (new_w, new_h))

    if overlay_resized.shape[2] == 4:
        alpha = overlay_resized[:, :, 3] / 255.0
        alpha = np.dstack([alpha] * 3)
        overlay_bgr = overlay_resized[:, :, :3]
    else:
        alpha = np.ones((new_h, new_w, 3), dtype=np.float32)
        overlay_bgr = overlay_resized

    bg_h, bg_w = bg.shape[:2]

    x1 = max(0, int(x))
    y1 = max(0, int(y))
    x2 = min(bg_w, int(x) + new_w)
    y2 = min(bg_h, int(y) + new_h)

    if x1 >= x2 or y1 >= y2:
        return bg

    overlay_x1 = int(x1 - x)
    overlay_y1 = int(y1 - y)
    overlay_x2 = int(x2 - x)
    overlay_y2 = int(y2 - y)

    roi = bg[y1:y2, x1:x2]
    overlay_cut = overlay_bgr[overlay_y1:overlay_y2, overlay_x1:overlay_x2]
    alpha_cut = alpha[overlay_y1:overlay_y2, overlay_x1:overlay_x2]

    if roi.shape != overlay_cut.shape:
        return bg

    blended = (overlay_cut * alpha_cut + roi * (1 - alpha_cut)).astype(np.uint8)
    result = bg.copy()
    result[y1:y2, x1:x2] = blended

    return result


def _get_anchor_point(landmarks, position, custom_landmark):
    if position == "CENTER":
        bbox = _get_face_bbox(landmarks)
        if bbox:
            cx = int((bbox[0] + bbox[2]) / 2)
            cy = int((bbox[1] + bbox[3]) / 2)
            return (cx, cy)
        return None

    lm_idx = _POSITION_LANDMARKS.get(position, 10)
    if custom_landmark is not None:
        lm_idx = custom_landmark

    return _get_landmark_coords(landmarks, lm_idx)


def _load_png(path):
    if not path or not os.path.exists(path):
        return None

    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    return img


def init(args, **kwargs):
    try:
        cfg = conf.get("FACEMASK")
        image_cfg = cfg.get("IMAGE", {})
        image_path = image_cfg.get("IMAGE_PATH", "")
        if image_path:
            _load_png(image_path)
        return True
    except Exception:
        io.echo_traceback("facemask init exception")
        return False


def detect(frame, context: ThreadSafeContext, **kwargs):
    try:
        if "FACEMASK" not in context:
            cfg = conf.get("FACEMASK")
            image_cfg = cfg.get("IMAGE", {})
            image_path = image_cfg.get("IMAGE_PATH", "")
            overlay_img = _load_png(image_path) if image_path else None

            context["FACEMASK"] = {
                "cfg": cfg,
                "overlay_img": overlay_img,
                "last_image_path": image_path,
                "faces": None,
                "timestamp": None,
                "error_state": False,
            }

        ns = context["FACEMASK"]
        ns["error_state"] = False

        cfg = conf.get("FACEMASK")
        ns["cfg"] = cfg

        image_cfg = cfg.get("IMAGE", {})
        current_path = image_cfg.get("IMAGE_PATH", "")
        last_path = ns.get("last_image_path", "")
        if current_path != last_path:
            ns["overlay_img"] = _load_png(current_path) if current_path else None
            ns["last_image_path"] = current_path

        face_ns = context.get("FACE")
        if face_ns and face_ns.get("faces"):
            faces_data = []
            for face_landmarks in face_ns["faces"]:
                bbox = _get_face_bbox(face_landmarks)
                if bbox:
                    face_width = bbox[2] - bbox[0]
                    face_height = bbox[3] - bbox[1]
                    faces_data.append({
                        "landmarks": face_landmarks,
                        "width": face_width,
                        "height": face_height,
                    })
            ns["faces"] = faces_data
        else:
            ns["faces"] = None

        ns["timestamp"] = time.time()
        context["FACEMASK"] = ns

    except Exception:
        if "FACEMASK" in context:
            context["FACEMASK"]["error_state"] = True
        io.echo_traceback("Facemask detect exception")


def draw(frame, context: ThreadSafeContext, **kwargs) -> np.ndarray:
    try:
        cfg = conf.get("FACEMASK")
    except Exception:
        return frame

    ns = context.get("FACEMASK")
    if not ns:
        return frame

    if ns.get("error_state"):
        return frame

    overlay_img = ns.get("overlay_img")
    faces_data = ns.get("faces")
    if not faces_data or overlay_img is None:
        grace_period = 0.35
        last_timestamp = ns.get("timestamp")
        current_time = time.time()
        if last_timestamp and (current_time - last_timestamp) > grace_period:
            return frame
        return frame

    image_cfg = cfg.get("IMAGE", {})
    adjust_cfg = cfg.get("ADJUST", {})

    position = image_cfg.get("POSITION", "TC")
    custom_landmark_cfg = image_cfg.get("LANDMARK", 10)
    scale = float(adjust_cfg.get("SCALE", 1.0))
    offset_x = int(adjust_cfg.get("OFFSET_X", 0))
    offset_y = int(adjust_cfg.get("OFFSET_Y", 0))

    working_frame = frame.copy()

    for face_data in faces_data:
        landmarks = face_data.get("landmarks")
        face_width = face_data.get("width", 100)
        face_height = face_data.get("height", 100)

        if position == "CENTER":
            bbox = _get_face_bbox(landmarks)
            if bbox:
                anchor = (int((bbox[0] + bbox[2]) / 2), int((bbox[1] + bbox[3]) / 2))
            else:
                anchor = None
        else:
            lm_idx = _POSITION_LANDMARKS.get(position, 10)
            if custom_landmark_cfg != 10:
                lm_idx = custom_landmark_cfg
            anchor = _get_landmark_coords(landmarks, lm_idx)
            if anchor is None:
                anchor = _get_landmark_coords(landmarks, 10)

        if anchor is None:
            continue

        png_width = overlay_img.shape[1]
        png_height = overlay_img.shape[0]

        if position in ("TC", "TL", "TR"):
            bbox = _get_face_bbox(landmarks)
            if bbox:
                left_x = bbox[0]
                right_x = bbox[2]
                top_y = bbox[1]
                bottom_y = bbox[3]
            else:
                left_x = anchor[0]
                right_x = anchor[0]
                top_y = anchor[1]
                bottom_y = anchor[1] + face_height

            target_width = right_x - left_x
            target_height = bottom_y - top_y
            dynamic_scale = (target_width / png_width) * scale
            scaled_width = int(png_width * dynamic_scale)
            scaled_height = int(png_height * dynamic_scale)

            if position == "TL":
                x = left_x + offset_x
                y = top_y + offset_y
            else:
                x = right_x - scaled_width + offset_x
                y = top_y + offset_y
            working_frame = _overlay_png(working_frame, overlay_img, x, y, dynamic_scale)
        else:
            dynamic_scale = (face_width / png_width) * scale
            scaled_width = int(png_width * dynamic_scale)
            scaled_height = int(png_height * dynamic_scale)
            x = anchor[0] - (scaled_width // 2) + offset_x
            y = anchor[1] + offset_y
            working_frame = _overlay_png(working_frame, overlay_img, x, y, dynamic_scale)

    return working_frame


def ui_schema(args=None, context=None) -> dict | None:
    return {
        "IMAGE": {
            "IMAGE_PATH": {
                "type": "file",
                "label": "PNG Image",
                "filters": [("PNG files", "*.png"), ("All files", "*.*")],
            },
            "POSITION": {
                "type": "radio",
                "enum": ["TL", "TC", "TR", "CENTER"],
                "label": "Position",
                "default": "TL",
            },
            "LANDMARK": {
                "type": "int",
                "min": 0,
                "max": 467,
                "label": "Landmark Index",
            },
        },
        "ADJUST": {
            "SCALE": {
                "type": "float",
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "label": "Scale",
            },
            "OFFSET_X": {
                "type": "int",
                "min": -200,
                "max": 200,
                "label": "Offset X",
            },
            "OFFSET_Y": {
                "type": "int",
                "min": -200,
                "max": 200,
                "label": "Offset Y",
            },
        },
    }


def buildargs(args, **kwargs):
    return None


def access(args, op, /, **kwargs):
    return True


def main(args, **kwargs):
    return True
