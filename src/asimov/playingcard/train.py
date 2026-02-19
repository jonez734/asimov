#!/usr/bin/env python3
"""
asimov.playingcard.train

Builds templates from raw card images.
Precomputes scaled and rotated templates for fast detection.
"""

import os
import cv2
import numpy as np
from glob import glob
from ..common import get_safe_path, logentry

from ..io import echo

# ------------------------------------------------------
# Configuration
# ------------------------------------------------------

ANGLES = [n for n in range(0, 360, 45)]
SCALES = [1.0,] # 0.5, 0.7, 0.9, 1.0, 1.1, 1.2]            # Optional scaling
PROPORTIONAL_CORNER = 0.25           # Fraction of card size
MIN_CORNER_SIZE = 60

def extract_templates(basedir, set_name, corner_size=None):
    set_dir = get_safe_path(basedir, "sets", set_name)
    templates = {}

    # iterate files (whatever your code already does)
    for fname in sorted(os.listdir(set_dir)):
        if not fname.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        full = os.path.join(set_dir, fname)
        img = cv2.imread(full, cv2.IMREAD_COLOR)
        if img is None:
            continue

        img_h, img_w = img.shape[:2]

        # If caller didn't provide corner_size, compute it proportionally
        if corner_size is None:
            # PROPORTIONAL_CORNER should be defined globally (e.g. 0.12)
            prop = PROPORTIONAL_CORNER
            cw = max(1, int(round(img_w * prop)))   # width
            ch = max(1, int(round(img_h * prop)))   # height
            corner_size = (cw, ch)  # (w, h)
        else:
            # normalize to ints and clamp to image size
            cw, ch = int(corner_size[0]), int(corner_size[1])
            cw = max(1, min(cw, img_w))
            ch = max(1, min(ch, img_h))
            corner_size = (cw, ch)

        # Note: we use img[:height, :width], so corner_size is (width, height)
        cw, ch = corner_size
        corner = img[:ch, :cw]  # slice safely

        # convert to grayscale if you want templates as single channel
        if corner.ndim == 3:
            corner = cv2.cvtColor(corner, cv2.COLOR_BGR2GRAY)

        # derive a key/name for this template from filename (strip ext)
        card_name = os.path.splitext(fname)[0]
        templates[card_name] = corner

    return templates, set_dir, corner_size

# ------------------------------------------------------
# Train function
# ------------------------------------------------------

def train(basedir, set_name):
    # Extract raw templates (dynamic corner)
    templates, set_dir, corner_size = extract_templates(
        basedir, set_name, corner_size=None
    )

    # Prepare scaled directory
    scaled_dir = get_safe_path(set_dir, "scaled")
    os.makedirs(scaled_dir, exist_ok=True)

    # Precompute all scaled and rotated templates
    for card_name, img in templates.items():
        for scale in SCALES:
            scaled = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

            for angle in ANGLES:
                rotated = rotate_image(scaled, angle)
                # Convert to grayscale if needed
                if rotated.ndim == 3:
                    rotated = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)

                filename = get_safe_path(scaled_dir, f"{card_name}_{scale:.2f}_{angle}.png")
                cv2.imwrite(filename, rotated)

    # Save metadata (not raw templates) for reference
    meta = {
        "card_names": list(templates.keys()),
        "corner_size": corner_size,
        "scales": SCALES,
        "angles": ANGLES,
    }
    np.savez_compressed(get_safe_path(set_dir, "templates.npz"), **meta)

    echo(f"[train] Precomputed templates saved in '{scaled_dir}'", end="\n")
    echo(f"[train] Metadata saved in '{get_safe_path(set_dir, 'templates_meta.npz')}'", end="\n")

# ------------------------------------------------------
# Utility for rotation
# ------------------------------------------------------

def rotate_image(img, angle):
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (h * sin))
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    return cv2.warpAffine(img, M, (new_w, new_h), flags=cv2.INTER_LINEAR)

# ------------------------------------------------------
# CLI
# ------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--basedir", required=True, help="Base directory of playingcards")
    parser.add_argument("--set", required=True, help="Card set name (folder)")
    args = parser.parse_args()

    train(args.basedir, args.set)
