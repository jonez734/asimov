"""
asimov.playingcard
Detects playing cards using precomputed template data.
"""

import cv2
import numpy as np

from ..io import echo
from ..common import ThreadSafeContext
from .. import conf

from . import cards
from .set import load as load_set
from .detect import detect


# ------------------------------------------------------------
# Initialization
# ------------------------------------------------------------

def init(args=None, context=None, **kwargs):
    """
    Loads the playing card set from args or config.
    """
    basedir = getattr(args, "basedir", None)
    if basedir is None:
        basedir = conf.PLAYINGCARD.get("BASEDIR", "$HOME/projects/playingcarddata")

    set_name = getattr(args, "set_name", None)
    if set_name is None:
        set_name = conf.PLAYINGCARD.get("SET_NAME", "bicycle")

    echo(f"{{reset}}- {{labelcolor}}Load set {{valuecolor}}'{set_name}{{labelcolor}}': ", end="", flush=True)
    if load_set(basedir, set_name) is True:
        echo("{green}[{checkmark} OK]{reset}", flush=True)
        return True
    else:
        echo("{red}[{crossmark}FAIL]{reset}", flush=True)
        return False


# ------------------------------------------------------------
# Lifecycle hooks
# ------------------------------------------------------------

def access(args, op, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def main(args, **kwargs):
    return True


# ------------------------------------------------------------
# Detection
# ------------------------------------------------------------

def detect(frame, context, **kwargs):
    """
    Detect playing card in frame.
    """
    # TODO: Implement actual detection using templates.py
    detected = context.get("playingcard_detected")
    if detected:
        echo(f"detect: {detected.get('name', 'unknown')}")
    return frame


# ------------------------------------------------------------
# Drawing overlay
# ------------------------------------------------------------

def draw(frame: np.ndarray, context: ThreadSafeContext):
    """
    Draws overlay info for detected card.
    """
    detected = context.get("playingcard_detected")
    if not detected:
        return frame

    text = f"{detected['name']} ({detected['angle']}°) [{detected['score']:.2f}]"
    cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
    return frame


# ------------------------------------------------------------
# Re-export shared utilities
# ------------------------------------------------------------

__all__ = [
    "cards",
    "RANKS",
    "SUITS",
    "RANK_DISPLAY",
    "SUIT_DISPLAY",
    "SUIT_SYMBOLS",
    "load_card_image",
    "get_card_path",
    "parse_card_string",
    "is_valid_card",
]
