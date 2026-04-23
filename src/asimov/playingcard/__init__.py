"""
asimov.playingcard
Detects playing cards using precomputed template data.
"""

import cv2
import numpy as np

from . import cards
from . import templates
from . import train
from . import util
from .set import load as load_set
from .detect import detect

# Use absolute imports that go through asimov's top-level namespace
# These work because asimov/io and asimov modules are accessible
from asimov.io import echo
from asimov.base import common
from asimov import conf

ThreadSafeContext = common.ThreadSafeContext

load = load_set
card_set = load_set


# ------------------------------------------------------------
# Initialization
# ------------------------------------------------------------


def init(args=None, context=None, **kwargs):
    """
    Loads the playing card set from args or config.
    """
    basedir = getattr(args, "basedir", None)
    if basedir is None:
        basedir = conf.CONF["PLAYINGCARD"].get(
            "BASEDIR", "$HOME/projects/playingcarddata"
        )

    set_name = getattr(args, "set_name", None)
    if set_name is None:
        set_name = conf.CONF["PLAYINGCARD"].get("SET_NAME", "bicycle")

    echo(
        f"{{reset}}- {{labelcolor}}Load set {{valuecolor}}'{set_name}{{labelcolor}}': ",
        end="",
        flush=True,
    )
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
    "detect",
    "load",
    "load_set",
    "set",
    "card_set",
    "templates",
    "train",
    "util",
    "init",
    "access",
    "buildargs",
    "main",
    "draw",
    "ThreadSafeContext",
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
