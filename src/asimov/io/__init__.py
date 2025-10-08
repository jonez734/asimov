"""
io.py – enhanced terminal output with commands, colors, word wrap, runtime variables, ACS chars, select emojis, and file paging.

Features:
- echo() and echo_file() with wordwrap, raw mode, and recursive command evaluation
- ANSI and C64 palettes (foreground/background)
- RGB color support with #RRGGBB or 255,255,255
- Cursor control: CURPOS, CUP, CUD, CUF, CUB, HOME
- Clear/erase: CLS (clear+home), ERASELINE, ERASEDISPLAY
- Scroll region: DECSTBM / STBM
- ACS characters with optional repeat
- Runtime variables: {var:<name>} or {<name>}
- Markdown-style attributes (**text**)
- Hard newline {f6}
- Recursive command expansion and aliases
"""

from .util import setbottombar

from .const import ESC

## from . import common
from .echo import echo, echo_file
## from .inputstr import inputstr
from .getch import getch_str as getch
from .inputstring import inputstring
from .palette import set_palette

__all__ = ["echo", "inputstring", "getch", "set_palette"]

# ----------------------------
# End of io.py
# ----------------------------
