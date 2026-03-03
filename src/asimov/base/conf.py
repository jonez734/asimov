# asimov_base/conf.py
# Shared configuration for Asimov packages
#
# DEPRECATED: This module is deprecated.
# All configuration has been merged into asimov.conf.
# Import from asimov.conf instead.
#
# This module will be removed in a future version.

import warnings

warnings.warn(
    "asimov.base.conf is deprecated. Import from asimov.conf instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from asimov.conf for backward compatibility
from asimov.conf import (  # noqa: F401, F811
    CAPTURE_DEVICE,
    CAPTURE_FPS,
    CAPTURE_HEIGHT,
    CAPTURE_WIDTH,
    EYES,
    FACE,
    FLOAT_CARD,
    FLOAT_PLAYINGCARD,
    GLITCH,
    GLITCH_DEFAULT_DATAMOSH_INTENSITY,
    GLITCH_DEFAULT_DATAMOSH_STRIPS,
    GLITCH_DEFAULT_GHOST_ALPHA,
    GLITCH_DEFAULT_GHOST_MAXLEN,
    GLITCH_DEFAULT_GHOST_SHIFT,
    GLITCH_DEFAULT_MAX_CONCURRENT,
    GLITCH_DEFAULT_MODULE,
    GLITCH_DEFAULT_SCANLINE_OPACITY,
    GLITCH_DEFAULT_SCANLINE_STEP,
    GLITCH_DEFAULT_VHS_FREQ,
    GLITCH_DEFAULT_VHS_INTENSITY,
    GLITCH_DEFAULT_WHITE_NOISE_INTENSITY,
    HAND,
    INDEXFINGERTIP,
    LOGGER_NAME,
    MOTIONBLUR,
    OVERLAYS,
    PLAYINGCARD,
    RECT,
    RECT_TOUCH,
    SCENE,
    WINDOW_NAME,
    FPS_OVERLAY,
)
