"""
asimov.playingcard
Detects playing cards using precomputed template data.
"""

import cv2

from ..io import echo
from ..common import safe_path

from ..common import ThreadSafeContext

from .set import load as load_set
from .detect import detect

import numpy as np


# ------------------------------------------------------------
# Initialization
# ------------------------------------------------------------

def init(basedir, set_name, context):
    """
    Loads the given set of playing card templates from disk.
    """
    echo(f"{{reset}}- {{labelcolor}}Load set {{valuecolor}}'{set_name}{{labelcolor}}': ", end="", flush=True)
    if load_set(basedir, set_name) is True:
        echo(f"{{green}}[{{checkmark}} OK]{{reset}}", flush=True)
        return True
    else:
        echo(f"{{red}}[{{crossmark}}FAIL]{{reset}}", flush=True)
        return False
    
# ------------------------------------------------------------
# Detection
# ------------------------------------------------------------

##def detect(frame, context, threshold=0.8):
##    """
##    Detects playing card from the given frame.
##    Updates and returns context.
##    """
##    name, angle, score = tpl.detect_card(frame, threshold)
##
##    if name is not None:
##        context["playingcard_detected"] = {
##            "name": name,
##            "angle": angle,
##            "score": score,
##        }
##
##    return context


# ------------------------------------------------------------
# Drawing overlay
# ------------------------------------------------------------

def draw(frame:np.ndarray, context:ThreadSafeContext):
    """
    Draws overlay info for detected card.
    """
    detected = context.get("playingcard_detected")
    if not detected:
        return frame

    text = f"{detected['name']} ({detected['angle']}°) [{detected['score']:.2f}]"
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    return frame

def load(filename: str, card_dir: str = "."):
    """
    Load a playing card PNG as RGBA (if available) and return as a NumPy array.

    Args:
        filename: Name of the card image file (e.g., "ace_of_spades.png").
        card_dir: Optional base directory (default ".").
    
    Returns:
        NumPy array representing the card image with alpha preserved.
    """
    # Delegate all path sanitation to safe_path()
    safe_full_path = safe_path(card_dir, filename)

    img = cv2.imread(safe_full_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not load card image: {safe_full_path}")
    return img
