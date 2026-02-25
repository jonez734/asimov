import os
import argparse

import cv2
import numpy as np

import cv2

from asimov.common import get_safe_path

import asimov.playingcard.templates as libtemplates

def load_templates(basedir, set_name):
    """
    Load all precomputed scaled/rotated templates from a directory.

    Args:
        scaled_dir (str): Path to the 'scaled' directory with template PNGs.

    Returns:
        dict: {template_name: grayscale_image}
    """
    
    templates = libtemplates.load_templates(basedir, set_name)
    if not templates:
        raise RuntimeError(f"No templates found in '{scaled_dir}'")
    return templates

#def scale_templates(templates, scale=1.0):
#    scaled = {}
#    for name, tmpl in templates:
#        tmpl = cv2.resize(tmpl, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
#        scaled[name] = tmpl
#    print(f"[load_templates] scaled {len(templates)} templates.")
#    return scaled

# Ensure all templates are grayscale
##for name, tmpl in templates.items():
##    if tmpl.ndim == 3:
##        templates[name] = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)

# -------------------------
# Camera capture
# -------------------------
cap = cv2.VideoCapture(0)  # adjust resolution if needed

# Downscale factor for faster matching
SCALE_FACTOR = 0.5
MATCH_THRESHOLD = 0.85  # tweak for confidence

def main(args=None, **kwargs):

    # -------------------------
    # Load templates once
    # -------------------------
    # Returns: dict[card_name] -> template image (grayscale)
    templates = load_templates(args.basedir, args.set_name)  # your precomputed scaled/rotated templates
##    templates = scale_templates(templates, scale=SCALE_FACTOR)
    

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert to grayscale and downscale
        frame_gray = frame
#        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_small = cv2.resize(frame_gray, None, fx=SCALE_FACTOR, fy=SCALE_FACTOR)

        match_found = False
        # -------------------------
        # Match templates
        # -------------------------
        for card in templates:
            for t in tmpl:
                res = cv2.matchTemplate(frame_small, t, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if max_val >= MATCH_THRESHOLD:
                    # Map coordinates back to original frame size
                    top_left = (int(max_loc[0] / SCALE_FACTOR), int(max_loc[1] / SCALE_FACTOR))
                    bottom_right = (
                        top_left[0] + int(tmpl.shape[1]),
                        top_left[1] + int(tmpl.shape[0])
                    )

                    cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
                    cv2.putText(frame, card_name, (top_left[0], top_left[1]-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                    
                    match_found = True
                    break  # early exit once we find a match

        # Display
        cv2.imshow("Card Detection Demo", frame)

        key = cv2.waitKey(1)
        if key == ord('q') or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Realtime playing card detection demo")
    parser.add_argument("--basedir", required=True, help="specify basedir for playingcard data")
#    parser.add_argument("--scaled-dir", required=True, help="Path to scaled templates directory")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index (default 0)")
    parser.add_argument("--scale-factor", type=float, default=0.5, help="Downscale factor for matching")
    parser.add_argument("--threshold", type=float, default=0.85, help="Matching threshold")
    parser.add_argument("--set-name", type=str, default="bicycle", help="Card set name")
    args = parser.parse_args()

    main(args)
