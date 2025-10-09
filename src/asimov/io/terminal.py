import os
from .const import MAX_TERMINAL_WIDTH

def size():
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except OSError:
        return 100, 30

def columns():
    try:
        sz = size()
        return sz[0]
    except OSError:
        return MAX_TERMINAL_WIDTH
