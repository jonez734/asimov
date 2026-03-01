"""
asimov.playingcard.templates

Loads precomputed card templates and performs fast detection.
"""

import os
import cv2
import numpy as np
from asimov.base.common import get_safe_path
from asimov.base import conf
from asimov.io import echo


# ------------------------------------------------------------
# Globals
# ------------------------------------------------------------

_loaded_templates = {}     # {set_name: [(name, img, scale, angle)]}
_corner_size = None
_loaded_set = None

# ------------------------------------------------------------
# Load all precomputed templates
# ------------------------------------------------------------

def load_templates(basedir=None, set_name=None):
    """
    Loads all precomputed templates from scaled/ under the given set.
    """
    if basedir is None:
        basedir = conf.PLAYINGCARD.get("BASEDIR", "$HOME/projects/playingcarddata")
    if set_name is None:
        set_name = conf.PLAYINGCARD.get("SET_NAME", "bicycle")

    basedir = os.path.expandvars(os.path.expanduser(basedir))
    global _loaded_templates, _corner_size, _loaded_set

    set_dir = get_safe_path(basedir, "sets", set_name)
    scaled_dir = get_safe_path(set_dir, "scaled")
    echo(f"load_templates.100: {scaled_dir=}", end="\n")
    npz_path = get_safe_path(set_dir, "templates.npz")

    if not os.path.exists(scaled_dir):
        raise FileNotFoundError(f"Scaled directory not found: {scaled_dir}")

    # Load metadata (corner size, etc.)
    if os.path.exists(npz_path):
        data = np.load(npz_path, allow_pickle=True)
        _corner_size = data.get("corner_size", None)

    templates = []
    for filename in os.listdir(scaled_dir):
        if not filename.lower().endswith(".png"):
            continue
        # filename format: queen_of_spades_1.00_15.png
        # filename without extension
        stem = filename[:-4]  # e.g., "10_of_clubs_0.80_0"
        echo(f"load_templates.260: {filename=}")
        # split from right to get angle and scale
        parts = stem.rsplit("_", 2)
        if len(parts) != 3:
            raise ValueError(f"Unexpected template filename format: {filename}")

        name_part = parts[0]      # "10_of_clubs"
        scale_part = parts[1]     # "0.80"
        angle_part = parts[2]     # "0"
        
        echo(f"{name_part=} {scale_part=} {angle_part=}", end="\n")

        path = get_safe_path(scaled_dir, filename)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

##        if scale != 1.0:
##            tmpl = cv2.resize(tmpl, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        templates.append((name_part, img, float(scale_part), int(angle_part)))

    _loaded_templates[set_name] = templates
    _loaded_set = set_name

    print(f"[playingcard] Loaded {len(templates)} precomputed templates from '{set_name}'")

    return templates

# ------------------------------------------------------------
# Fast detection using precomputed templates
# ------------------------------------------------------------

def detect_card(frame, threshold=0.8):
    """
    Detects which card corner matches best using precomputed templates.
    Expects frame to already be grayscale.
    """
    if _loaded_set is None:
        raise RuntimeError("No templates loaded. Call load_templates() first.")

#    if frame.ndim == 3:
#        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#    else:
#        frame_gray = frame
    frame_gray = frame

    best_match = (None, 0.0, 0, 0)  # (name, score, scale, angle)

    for (name, tmpl, scale, angle) in _loaded_templates[_loaded_set]:
        if frame_gray.shape[0] < tmpl.shape[0] or frame_gray.shape[1] < tmpl.shape[1]:
            continue

        res = cv2.matchTemplate(frame_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        if max_val > best_match[1]:
            best_match = (name, max_val, scale, angle)

    name, score, scale, angle = best_match
    if score >= threshold:
        return name, angle, score
    else:
        return None, None, 0.0
