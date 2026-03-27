from asimov.io import echo
from .set import is_loaded, _loaded_set_name
from asimov.base.common import ThreadSafeContext
import numpy as np


def detect(frame: np.ndarray, context: ThreadSafeContext):
    echo("asimov.playingcard.detect.100: called")
    if not is_loaded(_loaded_set_name):
        return frame
    return frame
