# asimov/playingcard/__init__.py
# Backward-compatible shim - re-exports from asimov_playingcard

from .asimov_playingcard import (
    cards,
    detect,
    load as load_set,
    set as card_set,
    templates,
    train,
    util,
    init,
    access,
    buildargs,
    main,
    draw,
)

__all__ = [
    "cards",
    "detect",
    "load",
    "set",
    "templates",
    "train",
    "util",
    "init",
    "access",
    "buildargs",
    "main",
    "draw",
]
