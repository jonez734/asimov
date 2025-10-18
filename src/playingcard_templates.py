#!/usr/bin/env python3
"""
playingcard_templates.py

Self-contained template management and detection module
for Asimov.playingcard.

Features:
- Build grayscale templates from PNGs
- Save/load templates as NPZ and PNG
- Precompute scaled templates for fast detection
- Detect rank/suit with rotation and scale invariance
- Works with poker, bridge, tarot, etc.
"""

import os
import cv2
import numpy as np
from glob import glob


# ======================================================
#  Template building and saving
# ======================================================

def build_templates(rank_dir, suit_dir, corner_size=(60, 60)):
    """Load PNGs and convert to grayscale templates."""
    ranks, suits = {}, {}

    for path in glob(os.path.join(rank_dir, "*.png")):
        name = os.path.splitext(os.path.basename(path))[0]
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"Warning: could not read {path}")
            continue
        img = cv2.resize(img, corner_size, interpolation=cv2.INTER_AREA)
        ranks[name] = img

    for path in glob(os.path.join(suit_dir, "*.png")):
        name = os.path.splitext(os.path.basename(path))[0]
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"Warning: could not read {path}")
            continue
        img = cv2.resize(img, corner_size, interpolation=cv2.INTER_AREA)
        suits[name] = img

    print(f"Loaded {len(ranks)} rank templates and {len(suits)} suit templates.")
    return ranks, suits


def save_templates_npz(rank_templates, suit_templates, filename="templates.npz"):
    """Save templates to compressed NPZ."""
    np.savez_compressed(filename, ranks=rank_templates, suits=suit_templates)
    print(f"Templates saved to {filename}")


def load_templates_npz(filename="templates.npz"):
    """Load templates from NPZ."""
    data = np.load(filename, allow_pickle=True)
    ranks = data["ranks"].item()
    suits = data["suits"].item()
    print(f"Templates loaded from {filename}")
    return ranks, suits


def save_templates_as_png(rank_templates, suit_templates, out_dir="processed_templates"):
    """Save preprocessed templates as PNG for inspection."""
    os.makedirs(out_dir, exist_ok=True)
    rank_dir = os.path.join(out_dir, "ranks")
    suit_dir = os.path.join(out_dir, "suits")
    os.makedirs(rank_dir, exist_ok=True)
    os.makedirs(suit_dir, exist_ok=True)

    for name, img in rank_templates.items():
        cv2.imwrite(os.path.join(rank_dir, f"{name}.png"), img)
    for name, img in suit_templates.items():
        cv2.imwrite(os.path.join(suit_dir, f"{name}.png"), img)

    print(f"Templates written under {out_dir}/")


# ======================================================
#  Precompute scaled templates
# ======================================================

def save_scaled_templates(rank_templates, suit_templates, out_dir="processed_templates_scaled", scales=(0.8,0.9,1.0,1.1,1.2)):
    """
    Save precomputed scaled versions of templates for faster detection.
    """
    os.makedirs(out_dir, exist_ok=True)
    rank_dir = os.path.join(out_dir, "ranks")
    suit_dir = os.path.join(out_dir, "suits")
    os.makedirs(rank_dir, exist_ok=True)
    os.makedirs(suit_dir, exist_ok=True)

    for name, img in rank_templates.items():
        for s in scales:
            scaled = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
            cv2.imwrite(os.path.join(rank_dir, f"{name}_{s:.2f}.png"), scaled)

    for name, img in suit_templates.items():
        for s in scales:
            scaled = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
            cv2.imwrite(os.path.join(suit_dir, f"{name}_{s:.2f}.png"), scaled)

    print(f"Scaled templates saved under {out_dir}/")


def load_scaled_templates(rank_dir="processed_templates_scaled/ranks",
                          suit_dir="processed_templates_scaled/suits"):
    """
    Load all precomputed scaled templates. Keys include scale in name, e.g., 'A_0.9'
    """
    def load_folder(folder):
        templates = {}
        for file in os.listdir(folder):
            if not file.lower().endswith(".png"):
                continue
            name = os.path.splitext(file)[0]  # e.g., 'A_0.9'
            path = os.path.join(folder, file)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            templates[name] = img
        return templates

    rank_templates = load_folder(rank_dir)
    suit_templates = load_folder(suit_dir)
    return rank_templates, suit_templates


# ======================================================
-#  Rotation and scale invariant detection
# ======================================================

def rotate_image(img, angle):
    """Rotate image around its center without cropping."""
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos, sin = np.abs(M[0, 0]), np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    return cv2.warpAffine(img, M, (new_w, new_h), flags=cv2.INTER_LINEAR)


def detect_rank_suit_from_corner_scaled(corner_img, rank_templates, suit_templates, threshold=0.75, angle_step=15):
    """
    Detect rank/suit using pre-scaled templates only.
    """
    best_rank, best_suit, best_angle, best_scale = None, None, None, None
    best_score = 0.0

    # Ranks
    for name, tmpl in rank_templates.items():
        scale = float(name.split("_")[-1])
        tmpl_base = tmpl
        res_img = corner_img.copy()
        for angle in range(0, 360, angle_step):
            rotated = rotate_image(res_img, angle)
            if rotated.shape[0] < tmpl_base.shape[0] or rotated.shape[1] < tmpl_base.shape[1]:
                continue
            res = cv2.matchTemplate(rotated, tmpl_base, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score and max_val >= threshold:
                best_rank, best_angle, best_scale, best_score = name.split("_")[0], angle, scale, max_val

    # Suits
    for name, tmpl in suit_templates.items():
        scale = float(name.split("_")[-1])
        tmpl_base = tmpl
        res_img = corner_img.copy()
        for angle in range(0, 360, angle_step):
            rotated = rotate_image(res_img, angle)
            if rotated.shape[0] < tmpl_base.shape[0] or rotated.shape[1] < tmpl_base.shape[1]:
                continue
            res = cv2.matchTemplate(rotated, tmpl_base, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > best_score and max_val >= threshold:
                best_suit, best_angle, best_scale, best_score = name.split("_")[0], angle, scale, max_val

    return best_rank, best_suit, best_angle, best_scale, best_score


# ======================================================
#  CLI / __main__
# ======================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build and test playing card templates")
    parser.add_argument("--ranks", default="templates/ranks", help="Directory with rank PNGs")
    parser.add_argument("--suits", default="templates/suits", help="Directory with suit PNGs")
    parser.add_argument("--corner", help="Optional corner PNG to test detection")
    parser.add_argument("--save", default="templates.npz", help="Output NPZ filename")
    parser.add_argument("--size", type=int, nargs=2, default=(60, 60), help="Template resize size (w h)")
    parser.add_argument("--scales", type=float, nargs="+", default=(0.8,0.9,1.0,1.1,1.2), help="Scales to precompute")
    args = parser.parse_args()

    # Step 1: Build templates
    ranks, suits = build_templates(args.ranks, args.suits, corner_size=tuple(args.size))

    # Step 2: Save templates
    save_templates_npz(ranks, suits, filename=args.save)
    save_templates_as_png(ranks, suits)

    # Step 3: Precompute scaled templates
    save_scaled_templates(ranks, suits, scales=args.scales)

    # Step 4: Optional detection test
    if args.corner:
        corner_img = cv2.imread(args.corner, cv2.IMREAD_GRAYSCALE)
        if corner_img is None:
            raise FileNotFoundError(args.corner)

        # Load scaled templates
        rank_scaled, suit_scaled = load_scaled_templates()

        rank, suit, angle, scale, score = detect_rank_suit_from_corner_scaled(corner_img, rank_scaled, suit_scaled)
        if rank or suit:
            print(f"Detected: {rank or '?'} of {suit or '?'}")
            print(f"Angle={angle}°, Scale={scale}, Score={score:.2f}")
        else:
            print("No confident match found.")
