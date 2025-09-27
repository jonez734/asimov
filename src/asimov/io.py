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

import os
import re
import sys
import time
import fcntl
import select
import platform
import threading

import tty, termios # get_cursor_position()

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterator

from bbsengine6 import screen

DEFAULT_PALETTE_NAME = "c64"

ESC   = "\x1B"
#CSI   = "\x9B"
CSI   = f"{ESC}["
BEL  = "\007"

# ----------------------------
# Token definition
# ----------------------------

# kind: WORD, WHITESPACE, F6, COMMAND, ACS, COLOR
# value: string content or command name
# args: positional args (list)
# kwargs: keyword args (dict)
# raw: original matched string
# text: whatever is to be output by _write_token()

@dataclass
class Token:
    kind: str                  # e.g., WORD, WHITESPACE, F6, RGB
    value: str = None          # the literal string or command
    args: List = field(default_factory=list)   # positional args
    kwargs: Dict = field(default_factory=dict) # keyword args
    text: str = field(default="") # {f6:3} -> \n*3, {home} -> \033[H, etc
    repeat: int = 1
    raw: Optional[str] = None                  # raw input that generated this token
    def __repr__(self):
        parts = [self.kind]
        if self.value:
            parts.append(f"value={repr(self.value)}") # repr(self.value))
        if self.args:
            parts.append(f"args={self.args}")
        if self.kwargs:
            parts.append(f"kwargs={self.kwargs}")
        if self.repeat:
            parts.append(f"repeat={self.repeat}")
        if self.text:
            parts.append(f"text={repr(self.text)}")
        if self.raw:
            parts.append(f"raw={repr(self.raw)}")
        return f"Token({', '.join(parts)})"

# Runtime variables dictionary
_runtime_vars = {}

_runtime_vars.update({"cls": "{erasedisplay}{home}"})
_runtime_vars.update({"home": "{curpos:1,1}"})

##? _runtime_vars.update("/all", "{reset}")

def set_var(name, value):
    """Set a runtime variable for use in {var:<name>} or {<name>} commands."""
    _runtime_vars[name] = value

def get_var(name, default=None):
    return _runtime_vars.get(name, default)

_current_input_stream = sys.stdin
_current_output_stream = sys.stdout
_current_output_stream_lock = threading.Lock()

_current_stream = sys.stdout
def set_output_stream(stream):
    global _current_output_stream
    _current_output_stream = stream

def set_input_stream(stream):
    global _current_input_stream
    _current_input_stream = stream

# ----------------------------
# ANSI / C64 color palettes
# ----------------------------
def rgb(fgbg, triplet):
    """Return ANSI SGR sequence for foreground (38) or background (48). Spec can be #RRGGBB or (r,g,b)"""
    if isinstance(triplet, str) and triplet.startswith("#") and len(triplet) == 7:
        r, g, b = int(triplet[1:3], 16), int(triplet[3:5], 16), int(triplet[5:7], 16)
    else:
        raise ValueError(f"Invalid RGB spec: {triplet=}")

    result = f"{CSI}{fgbg};2;{r};{g};{b}m"
#    print(f"rgb.100: {repr(result)=}")
    return result

def _parse_rgb(argstr: str) -> Token:
    """
    Parse rgb commands:
      {rgb:255,0,255}
      {rgb:#FF00FF}
      {rgb:#F0F}
      {rgb} (defaults to black)
    Returns Token with kwargs={"r":..,"g":..,"b":..}
    """
    r = g = b = 0  # default black

    if argstr:
        argstr = argstr.strip()

        # Hex form
        if argstr.startswith("#"):
            hexstr = argstr
            if len(hexstr) == 4:  # #RGB shorthand
                hexstr = "#" + "".join(ch * 2 for ch in hexstr[1:])
            hexstr = hexstr.upper()
            r = int(hexstr[1:3], 16)
            g = int(hexstr[3:5], 16)
            b = int(hexstr[5:7], 16)

        else:
            # Comma-separated ints
            parts = [p.strip() for p in argstr.split(",")]
            if len(parts) >= 3:
                r, g, b = (int(parts[0]), int(parts[1]), int(parts[2]))
            elif len(parts) == 4:
                r, g, b, a = (int(parts[0]), int(parts[1]), int(parts[2]))

    return Token(kind="COMMAND", value="rgb", args=(), kwargs={"r": r, "g": g, "b": b})

# ANSI palette (foreground)
ansi_palette = {
    "black":   f"{CSI}30m",
    "red":     f"{CSI}31m",
    "green":   f"{CSI}32m",
    "yellow":  f"{CSI}33m",
    "blue":    f"{CSI}34m",
    "magenta": f"{CSI}35m",
    "cyan":    f"{CSI}36m",
    "white":   f"{CSI}37m",
    # Light colors
    "lightblack":   f"{CSI}90m",
    "lightred":     f"{CSI}91m",
    "lightgreen":   f"{CSI}92m",
    "lightyellow":  f"{CSI}93m",
    "lightblue":    f"{CSI}94m",
    "lightmagenta": f"{CSI}95m",
    "lightcyan":    f"{CSI}96m",
    "lightwhite":   f"{CSI}97m",
    # Reset
##    "reset":        f"{CSI}0m",
}

# C64 palette
c64_palette = {
    'black': rgb(38, "#000000"),
    'white': rgb(38, "#ffffff"),
    'red': rgb(38, "#880000"),
    'cyan': rgb(38, "#aaffee"),
    'purple': rgb(38, "#cc44cc"),
    'green': rgb(38, "#00cc55"),
    'blue': rgb(38, "#0000aa"),
    'yellow': rgb(38, "#eeee77"),
    'orange': rgb(38, "#dd8855"),
    'brown': rgb(38, "#664400"),
    'lightred': rgb(38, "#ff7777"),
    'lightcyan': rgb(38, "#33ffff"),
    'lightpurple': rgb(38, "#ff77ff"),
    'lightgreen': rgb(38, "#aaff66"),
    'lightblue': rgb(38, "#0088ff"),
    'lightgray': rgb(38, "#bbbbbb")
}

def set_palette(palette_name):
    global _current_palette
    if palette_name == "ansi":
        _current_palette = ansi_palette
    elif palette_name == "c64":
        _current_palette = c64_palette

def get_palette(name=DEFAULT_PALETTE_NAME):
##    print(f"get_palette.100: {name=}")
    if name == "c64":
        return c64_palette
    elif name == "ansi":
        return ansi_palette
    return None

def get_current_palette():
    return _current_palette

def get_palette_entry(name):
    global _current_palette
##    print(f"get_palette_entry.100: {name=}")
    if _current_palette is None:
        print(f"setting _current_palette")
        set_palette(DEFAULT_PALETTE_NAME)

    return _current_palette[name]

# Background color aliases
def make_bg(palette):
    bg = {}
    for k, v in palette.items():
        bg[f"bg{k}"] = v.replace("38", "48")
    return bg

c64_palette.update(make_bg(c64_palette))
#ansi_palette.update(make_bg(ansi_palette))

_current_palette = get_palette(DEFAULT_PALETTE_NAME).copy()

# ----------------------------
# ACS characters
# ----------------------------
_acs_map = {
    # Box drawing
    "ulcorner": "l",    # ┌
    "urcorner": "k",    # ┐
    "llcorner": "m",    # └
    "lrcorner": "j",    # ┘
    "hline":    "q",    # ─
    "vline":    "x",    # │
    "ttee":     "w",    # ┬
    "btee":     "v",    # ┴
    "ltee":     "u",    # ┤
    "rtee":     "t",    # ├
    "plus":     "n",    # ┼

    # Other symbols
    "diamond":      "`",  # ◆
    "checkerboard": "a",  # ▒
    "ht":           "b",  # HT symbol
    "ff":           "c",  # FF symbol
    "cr":           "d",  # CR symbol
    "lf":           "e",  # LF symbol
    "degree":       "f",  # °
    "pluminus":     "g",  # ±
    "board":        "h",  # board of squares
    "lantern":      "i",  # lantern / scan line / bell symbol
    "scan1":        "o",  # scan line 1
    "scan3":        "p",  # scan line 3
    "scan7":        "r",  # scan line 7
    "scan9":        "s",  # scan line 9
    "lequal":       "y",  # ≤
    "gequal":       "z",  # ≥
    "pi":           "{",  # π
    "nequal":       "|",  # ≠
    "sterling":     "}",  # £
    "bullet":       "~",  # • / ≈

    # Extras sometimes present in DEC tables
    "notdef":       "^",  # undefined glyph
    "space":        "_",  # blank space
}

_unicode = {
    "ulcorner":    "\u250C", # ┌
    "urcorner":    "\u2510", # ┐
    "llcorner":    "\u2514", # └
    "lrcorner":    "\u2518", # ┘
    "hline":       "\u2500", # ─
    "vline":       "\u2502", # │
    "ttee":        "\u252C", # ┬
    "btee":        "\u2534", # ┴
    "ltee":        "\u251C", # ├
    "rtee":        "\u2524", # ┤
    "cross":       "\u253C", # ┼
    "dblhline":    "\u2550", # ═
    "dblvline":    "\u2551", # ║
    "dblul":       "\u2554", # ╔
    "dblur":       "\u2557", # ╗
    "dblll":       "\u255A", # ╚
    "dbllr":       "\u255D", # ╝
    "arrow":       "\u2192", # →
    "arrow_left":  "\u2190", # ←
    "arrow_up":    "\u2191", # ↑
    "arrow_right": "\u2192", # →
    "arrow_down":  "\u2193", # ↓
}

# https://stackoverflow.com/questions/3220031/how-to-filter-or-replace-unicode-characters-that-would-take-more-than-3-bytes
# https://medium.com/analytics-vidhya/how-to-print-emojis-using-python-2e4f93443f7e
_emoji = {
  "grin":                   "\U0001f600",
  "smile":                  "\U0001f642",
  "rofl":                   "\U0001f923",
  "wink":                   "\U0001f609",
  "thinking":               "\U0001f914",
  "sunglasses":             "\U0001f60e",
  "100":                    "\U0001f4af",
  "thumbup":                "\U0001f44d",
  "thumbdown":              "\U0001f44e",
  "vulcan":                 "\U0001f596",
  "spiral":                 "\U0001f4ab",
  "fire":                   "\U0001f525",
  "bank":                   "\U0001f3e6",
  "house":                  "\U0001f3e0",
  "military-helmet":        "\U0001fa96",
  "door":                   "\U0001f6aa",
  "receipt":                "\U0001f9fe",
  "newspaper":              "\U0001f4f0",
  "prince":                 "\U0001f934",
  "princess":               "\U0001f478",
  "thread":                 "\U0001f9f5",
  "ice":                    "\U0001f9ca",
  "moneybag":               "\U0001f4b0",
  "person":                 "\U0001f9d1",
  "sun":                    "\U00002600", # @see https://emojipedia.org/sun/
  "thunder-cloud-and-rain": "\U000026C8", # @see https://emojipedia.org/cloud-with-lightning-and-rain/
  "crop":                   "\U0001F33E", # @see https://emojipedia.org/sheaf-of-rice/
  "horse":                  "\U0001F40E", # @see https://emojipedia.org/horse/
  "cactus":                 "\U0001F335", # @see https://emojipedia.org/cactus/
  "ship":                   "\U0001F6A2", # @see https://emojipedia.org/ship/
  "wood":                   "\U0001FAB5", # @see https://emojipedia.org/wood/
  "link":                   "\U0001F517", # @see https://emojipedia.org/link/
  "anchor":                 "\U00002693", # @see https://emojipedia.org/anchor/
  "ballot-box":             "\U0001F5F3", # @see https://emojipedia.org/ballot-box-with-ballot/ @blacklist breaks monospace font
  "building":               "\U0001F3DB", # @see https://emojipedia.org/classical-building/
  "envelope":               "\U00002709", # @see https://emojipedia.org/envelope/
  "dolphin":                "\U0001F42C", # @see https://emojipedia.org/dolphin/
  "bellhop-bell":           "\U0001F6CE", # @see https://emojipedia.org/bellhop-bell/
  "hotel":                  "\U0001F3E8", # @see https://emojipedia.org/hotel/
  "mousetrap":              "\U0001FAA4", # @see https://emojipedia.org/mouse-trap/

  "waninggibbousmoon":      "\U0001F316",
  "waxinggibbousmoon":      "\U0001F314",
  "waningcrescentmoon":     "\U0001F318",
  "waxingcrescentmoon":     "\U0001F312",
  "lastquartermoon":        "\U0001F317",
  "firstquartermoon":       "\U0001F313",
  "newmoon":                "\U0001F311",
  "fullmoon":               "\U0001F315",

  "sco":                    "\U0000264F", # @see https://emojipedia.org/search/?q=zodiac
  "sag":                    "\U00002650",
  "cap":                    "\U00002651",
  "aqu":                    "\U00002652",
  "pic":                    "\U00002653",
  "ari":                    "\U00002648",
  "tau":                    "\U00002649",
  "gem":                    "\U0000264A",
  "can":                    "\U0000264B",
  "leo":                    "\U0000264C",
  "vir":                    "\U0000264D",
  "lib":                    "\U0000264E",

  "package":                "\U0001F4E6", # @since 20220907 @see https://emojipedia.org/package/
  "compass":                "\U0001F9ED", # @since 20220907
  "worldmap":               "\U0001F5FA", # @since 20220916

  "wolf":                   "\U0001F43A", # @since 20221002
  "person":                 "\U0001F9D1",

  "supervillian":           "\U0001F9B9", # @since 20221016
  "joker":                  "\U0001F0CF", # @since 20221127

  "warning":                "\U000026A0",
  "stopsign":               "\U0001F6D1",

  "dragon":                 "\U0001F409", # @since 20230716 for empyre
  "tree":                   "\U0001F333", # @since 20230824 for empyre
  "wood":                   "\U0001FAB5", # @since 20230824 for empyre

  "cityscape":              "\U0001F3D9", # @since 20230827 for empyre
  "maint":                  "\U0001F6E0", # @since 20230827 for empyre, mm
  "axe":                    "\U0001FA93", # @since 20230827 for mm

  "desert":                 "\U0001F3DC", # @since 20240107 for empyre

  "shopping":               "\U0001F6CD", # @since 20240128

  "farmer":                 "\U0001F9D1", # @since 20240415 for empyre

  "zap":                    "\U000026A1", # @since 20240422 for weather

  "palmtree":               "\U0001F334",
  "evergreentree":          "\U0001F332",

  "tophat":                 "\U0001F3A9",
  "magicwand":              "\U0001FA84",

  "mercenary":				u"\U0001F977",

  "checkmark":              u"\U00002705",
  "crossmark":              u"\U0000274E",
}

# ----------------------------
# Command patterns
# ----------------------------
command_patterns = [
    # hard newline
    ("F6",       r'\{f6(?::(?P<repeat>\d+))?\}'),

    # reset all attributes
    ("RESET",    r'\{/?reset\}'),

    # clear screen (ED modes: 0=down, 1=up, 2=entire)
    ("ERASEDISPLAY", r'\{erasedisplay(?::(?P<mode>[012]))?\}'),

    # home: equivalent to CURPOS 1,1
    ("HOME",     r'\{home\}'),

    # cursor positioning: optional y and x, 1-based
    ("CURPOS",   r'\{curpos(?::(?P<y>\d+)(,(?P<x>\d+))?)?\}'),

    # erase line: EL modes: 0=right, 1=left, 2=entire
    ("ERASELINE", r'\{(?:eraseline|el)(:(?P<mode>[012]))?\}'),

    # cursor horizontal absolute (CHA)
    ("CHA",      r'\{cha(:(?P<chanum>\d{1,3}))?\}'),

    # cursor movements (repeat n)
    ("CUP",      r'\{cup|cursorup(?::(?P<repeat>\d+))?\}'),
    ("CUD",      r'\{cud|cursordown(?::(?P<repeat>\d+))?\}'),
    ("CUF",      r'\{cuf|cursorforward|cursorleft(?::(?P<repeat>\d+))?\}'),
    ("CUB",      r'\{cub|cursorright|cursorback|cursorbackward(?::(?P<repeat>\d+))?\}'),

    # RGB colors, fg by default
    ("RGB",      r'\{rgb(?::(?P<fgbg>fg|bg))?:(?P<spec>[#\d,]+)\}'),

    # ACS characters (optional repeat)
    ("ACS",      r'\{acs:(?P<name>\w+)(?::(?P<repeat>\d+))?\}'),

    # run-time variables
    ("VAR",      r'\{var:(?P<name>\w+)\}'),
]

_command_handlers = {
    # cursor movements (repeat n)
    "cuu":     r'cup|cuu|cursorup',
    "cud":     r'cud|cursordown',
    "cuf":     r'cuf|cursorforward|cursorright',
    "cub":     r'cub|cursorleft|cursorback|cursorbackward',
    "curpos":  r'curpos',

    "decsc":   r'decsc|savecursor',
    "decrc":   r'decrc|restorecursor',

    "decstbm": r'decstbm',

    "acs":     r'acs',
    "f6":      r'f6',

    # runtime variables
    "var": r'var',
    "attr": r'attr',

    # rgb color
    "rgb": r'rgb',

    # reset attributes and color
    "reset": r'reset',

    # erase display
    "ed": r'ed|erasedisplay',

    # erase line
    "elo": r'el|eraseline',
    "bel": r'bel|bell',
}

_compiled_command_handlers = [(kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in _command_handlers.items()]

_whitespace_re = re.compile(r'(\s+)')
_word_re = re.compile(r'[^\s{}]+')
##_command_re = re.compile(r"""
##    \{
##    (?P<name>/?[a-zA-Z_][a-zA-Z0-9_-]*)  # command name: first char letter/_ , rest letters/digits/_/-
##    (?:                                # optional args block
##        [:,]                           # args sep "," or ":"
##        (?P<params>[^}]*)              # everything up to the closing brace
##    )?
##    \}
##""", re.VERBOSE | re.IGNORECASE)

_command_re = re.compile(r"\{(?P<name>/?[a-zA-Z_][a-zA-Z0-9_]*)(?::?(?P<params>[^}]*))\}", re.IGNORECASE)
_emoji_re = re.compile(r":(?P<name>[\w _-]+):", re.IGNORECASE)

# ----------------------------
# Aliases / command expansion
# ----------------------------
command_aliases = {
##    "cls": "{erasedisplay}{home}",
    "reset": "{/reset}",
}

# ----------------------------
# Utilities
# ----------------------------
def get_terminal_size():
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except OSError:
        return 100, 30

def get_terminal_width():
    try:
        sz = get_terminal_size()
        return sz[0]
    except OSError:
        return 100

# --------------------------
# DSR (Device Status Report)
# --------------------------

def _read_terminal_response(terminator: str) -> str | None:
    """
    Reads characters from the terminal until the specified terminator is received
    or the timeout expires.

    Args:
        terminator: Character that ends the terminal response (e.g., 'R' for CPR).
        timeout: Maximum seconds to wait for a response.

    Returns:
        The raw response string if successful, or None if timeout/failure occurs.
    """
    fd = _current_input_stream.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)  # set raw/cbreak mode to read characters immediately
        response = ""
        while True:
            ch = _current_input_stream.read(1)
            response += ch
            if ch == terminator:
                return response
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def get_dsr(function:str):
    if function == "status": # DSR
        code = "5"
        terminator = "n"
    elif function == "cursor":
        code = "6"
        terminator = "R"

    sys.stdout.write(f"{CSI}{code}n")
    sys.stdout.flush()
    return _read_terminal_response(terminator)

def get_cursor_position():
    """Query the terminal for current cursor position:
Cursor Position (CPR / DECURSORPOS)
    Query: ESC [ 6 n
    Response: ESC [ <row> ; <col> R
"""
    response = get_dsr("cursor")
    if response and response.startswith(f"{ESC}[") and response.endswith("R"):
        parts = response[2:-1].split(";")
        row, col = int(parts[0]), int(parts[1])
        return row, col

def get_terminal_status():
    """Device Status (DECTST / terminal readiness)

    Query: ESC [ 5 n

    Response: ESC [ 0 n → OK, ESC [ 3 n → error
"""

    response = send_dsr("status")
    if response and response.startswith(f"{CSI}") and response.endswith("R"):
        parts = response[2:-1].split(";")
        row, col = int(parts[0]), int(parts[1])
        return row, col

    # Save terminal settings
    fd = _current_input_stream.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write(f"{CSI}0n")  # DSR to query status
        sys.stdout.flush()

        # Read response ESC [ row ; col R
        response = read_terminal_response("R")
        if response.startswith(f"{CSI}") and response.endswith("n"):
            part = int(response[2])
            if part == 0:
                return True
            elif part == 3:
                return False
            else:
                return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
# ----------------------------
# Tokenizer
# ----------------------------
def tokenize(text):
    """Yields Token(kind, value, args, kwargs, raw)"""
    pos = 0
    while pos < len(text):
        # Whitespace
        m = _whitespace_re.match(text, pos)
        if m:
            # emit a single WHITESPACE token
            token = Token(
                kind="WHITESPACE",
                value=m.group(1),       # optional semantic info
                repeat=len(m.group(0)), # total length of run
                text=None,              # to be filled by handler
                raw=m.group(0)
            )
##            print(f"tokenize.100: {tok=}")
            yield from _handle_whitespace(token)
            pos = m.end()
            continue

        # commands
        m = re.match(_command_re, text[pos:])
        if m:
            name = m.group("name").lower()
            params = m.group("params") or ""
            args, kwargs = parse_command_params(name, params)

##            print(f"tokenize.200: {name=} {args=} {m.group(0)=}")

            tok = Token(kind="COMMAND", value=name, args=tuple(args), kwargs=kwargs, raw=m.group(0))
            yield from _handle_command(tok)
            pos += m.end()
            continue

#        m = re.match(_compiled_command_handlers[1], m.group("name").lower())
#        if m:
#            tok = Token(_compiled_command_handler[0], raw=m.group(0))

        m = re.match(_emoji_re, text[pos:])
        if m:
            name = m.group("name").lower()
            tok = Token(kind="EMOJI", value=name, raw=m.group(0))
            yield from _handle_emoji(tok)
            pos += m.end()
            continue

        # word
        m = re.match(_word_re, text[pos:])
        if m:
            # WORD: span until next whitespace or command
            end = pos + 1
            while end < len(text) and not text[end].isspace() and text[end] != "{":
                end += 1
            yield Token("WORD", text[pos:end], [], {}, text[pos:end])
            pos = end
            continue

        run = text[pos:]
        yield Token("UNKNOWN", value=run, text=run)
        pos += len(text[pos:])

# ----------------------------
# token handlers
# ----------------------------
def _handle_word(token):
    global _acs, _raw

    token.text = token.value
    token.raw = token.value
    token.repeat = 1
    

    if _acs and not _raw:
        _acs = False
        yield Token("CONTROL", text=f"{ESC}(B")

    yield token

def _handle_whitespace(token):
    """
    Consolidate repeated whitespace characters into tokens.
    For example, a run of 3 newlines becomes:
        Token(kind="WHITESPACE", value="\n", repeat=3, text="\n\n\n")
    """
    global _acs, _raw

    if _acs:
        _acs = False
        if not _raw:
            yield Token("CONTROL", text=f"{ESC}(B")

    run = token.value
    i = 0
    while i < len(run):
        ch = run[i]
        repeat = 1
        while i + repeat < len(run) and run[i + repeat] == ch:
            repeat += 1
        yield Token("WHITESPACE",
            value=ch,           # the character itself (' ', '\t', or '\n')
            repeat=repeat,       # how many times it repeats
            text=ch * repeat,    # string that will be written
            raw=ch * repeat
        )
        i += repeat

# save/restore cursor attributes
@dataclass
class TerminalState():
    cursor_row = 1
    cursor_col = 1
    wordwrap  = True
    has_color = True
    hidden = False
    def __repr__(self):
        return f"TerminalState({self.cursor_row=} {self.cursor_col=})"

_terminal_states = []

_wordwrap = True
_color = True
_acs = False
_cursor_row = 1
_cursor_col = 1
_raw = False

def _handle_decsc(token):
    global _terminal_states

    (row, col) = get_cursor_position()
    print(f"_handle_decsc.100: {token=}")
    state = TerminalState()
    state.cursor_row = row
    state.cursor_col = col
    state.wordwrap = _wordwrap
    state.color = _color
    _terminal_states.append(state)

##    print(f"_handle_decsc.120: {state=} {_terminal_states=}")
    return iter(())

def _handle_decrc(token):
    global _color, _cursor_col, _cursor_row, _wordwrap, _terminal_states
##    print(f"_handle_decrc.100: {_terminal_states=}")
    if len(token.args) == 1:
        state = _terminal_states.pop()
    else:
        state = _terminal_states[0]

    yield Token("CURPOS", args=(state.cursor_row, state.cursor_col), raw=token.raw, text=f"{CSI}{state.cursor_row};{state.cursor_col}H")
    yield Token("WORDWRAP", raw=token.raw, text=f"") # [WORDWRAP: {_wordwrap}]")
    _color = state.color
    _cursor_row = state.cursor_row
    _cursor_col = state.cursor_col
    _wordwrap = state.wordwrap

def _handle_acs(token):
    global _acs, _raw

##    print(f"_handle_acs.200: {token=}")
    if token.value == "acs":
        name = token.args[0]
        repeat = int(token.args[1]) if len(token.args) > 1 else 1
    else:
        token.value in _acs_map
        name = token.value
        repeat = int(token.args[0]) if token.args else 1

    if not _acs:
        _acs = True
        if not _raw:
            yield Token("CONTROL", text=f"{ESC}(0")
    else:
        _acs = False

    token.kind = "ACS"
    token.text = _acs_map.get(name, "?")*repeat

    yield token
    return

def _handle_var(token):
    var_name = token.args[0] if token.args else token.value
    var_val = _runtime_vars.get(var_name, "")
    # recursively tokenize the value of the variable
    for t in tokenize(var_val):
        yield t
    return

def _handle_rgb(token):
    print(f"_handle_rgb.100: {token=}")
    if len(token.args) == 2:
        mode = 38 if token.args[0] == "fg" else 48
        token.text = rgb(mode, token.args[1])
        yield token
        return
    elif len(token.args) == 1:
        token.text = rgb(38, token.args[0])
        yield token
        return

    raise ValueError("Argument Error")
    return

def _handle_curpos(token):
    global _cursor_col, _cursor_row

##    print(f"_handle_curpos.100: foo")
    y = int(token.args[0]) if token.args else 1
    x = int(token.args[1]) if len(token.args) > 1 else 1
    token.text = f"{CSI}{y};{x}H"
    yield token
    _cursor_col = x
    _cursor_row = y
    
def _handle_f6(token):
    global _cursor_col

    repeat = int(token.args[0]) if token.args else 1
    token.repeat = repeat
    token.text = "\n"*repeat
    token.kind = "F6"

    yield token

    _cursor_col = 0

    return

def _handle_home(token):
    token.text = f"{CSI}H"
    yield token
    return

# erasedisplay
# tobottom = 1, totop = 2, default = 0 = full
def _handle_ed(token):
    print(f"**** _handle_ed.100: {token=}")
    mode = int(token.args[0]) if len(token.args) == 1 else 2
    token.text = f"{CSI}{mode}J"
    yield token

# 0 = clear right of cursor
# 1 = clear left of cursor
# 2 = clear whole line
# EL0 – Erase in Line (cursor to end of line)
def _handle_elo(token):
    print(f"**** _handle_ed.100: {token=}")
    mode = int(token.args[0]) if len(token.args) == 1 else 0
    token.text = f"{CSI}{mode}K"
    yield token

def _handle_cuu(token):
##    print(f"_handle_cuu.100: {token.args=}")
    repeat = token.args[0] or 1
##    token.kind = "CURSOR"
    token.repeat = repeat
    token.text = f"{CSI}{repeat}A"
    yield token

def _handle_cud(token):
    repeat = token.args[0] or 1
##    token.kind = "CURSOR"
    token.repeat = 1
    token.text = f"{CSI}{repeat}B"
#    print(f"_handle_cud.100: {token=}")
    yield token
    return

def _handle_cuf(token):
    repeat = int(token.args[0]) or 1
##    token.kind = "CURSOR"
    token.repeat = repeat
    token.text = f"{CSI}{repeat}C"
    yield token

def _handle_cub(token):
    repeat = int(token.args[0]) or 1
    print(f"_handle_cub.100: {token=}")
    token.repeat = 1
    token.text = f"{CSI}{repeat}D"
    yield token
    return

def _handle_decstbm(token):
    token.repeat = 1
    if len(token.args) == 0:
        token.text = f"{CSI}r"
        yield token
        return

    t = token.args[0]
    b = token.args[1]
    if t == "0" and b == "0":
        token.text = f"{CSI}r"
    else:
        token.text = f"{CSI}{t};{b}r"
    yield token
    return

def _handle_reset(token):
    token.repeat = 1
    token.text = f"{ESC}[0m"
    yield token

@dataclass
class Attr:
    start: str
    end: str
    state: bool = field(default=None)

# Global stack of active attributes
## ATTR_STACK: list[Attr] = []

ANSI_ATTRS = {
    "bold": Attr(start=f"{CSI}1m", end=f"{CSI}22m"),
    "italic": Attr(start=f"{CSI}3m", end=f"{CSI}23m"),
    "underline": Attr(start=f"{CSI}4m", end=f"{CSI}24m"),
    "strike": Attr(start=f"{CSI}9m", end=f"{CSI}29m"),
    "code": Attr(start=f"{CSI}7m", end=f"{CSI}27m"),  # inverse
    "inverse": Attr(start=f"{CSI}7m", end=f"{CSI}27m"),  # inverse
}

## ATTR_RE = re.compile(r"(/?\w+)")

def _handle_attr(token: Token):
    """
    Mutate a Token containing {attr} or {/attr} to emit corresponding ANSI sequence(s).
    Each ANSI sequence is yielded as a separate Token.
    """

##    print(f"_handle_attr.100: {token.kind=} {token.value=}")

    name = token.value.lstrip("/")
    attr = ANSI_ATTRS.get(name)

    # closing {/bold}
    if token.value.startswith("/"):
        # closing attribute
        attr.state = False
        token.kind = "ATTR"
        token.text = attr.end
        yield token
        return

    # opening attribute {bold}
    attr.state = True
    token.kind = "ATTR"
    token.text = attr.start
    yield token
    return
    

def _handle_emoji(token):
    if token.value in _emoji:
        token.text = _emoji[token.value]
    else:
        token.text = token.raw
    yield token


_previous_token = Token("UNKNOWN")

PARAM_SPLIT_RE = re.compile(r"[:,]")
def parse_command_params(name, params):
    args = [] # [name,]
    kwargs = {}
    if not params:
        return args, kwargs

    for part in PARAM_SPLIT_RE.split(params):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            kwargs[k.strip()] = v.strip()
        elif part:
            args.append(part)
    return args, kwargs

def _handle_unknown(token):
    token.text = f"{token.kind=}: no registered handler"
    yield token

def handler_dispatch(token):
    """Yield from the appropriate handler given a token."""

    cmd = token.value.lower()

    for kind, regex in _compiled_command_handlers:
        if regex.fullmatch(cmd):
            handler_name = f"_handle_{kind}"
            handler = globals().get(handler_name)
            if callable(handler):
                result = handler(token)
                if result is None:
                    return

                if hasattr(result, "__iter__") and not isinstance(result, str):
                    yield from result
                    return
                break
    token.text = str(token.raw)
    yield token
    return False

def _handle_bel(token):
    token.text = BEL
    yield token

def _handle_command(token, palette=None, vars=None):
    """
    Processes a single command token and yields one or more Tokens.
    
    Args:
        token: Token of kind COMMAND from tokenize()
        _runtime_vars: optional dict of runtime variables
    Yields:
        Token instances (WORD, WHITESPACE, F6, etc.)
    """
##    if _runtime_vars is None:
##        _runtime_vars = {}

    global _acs

    # command name is lowercase
    cmd = token.value.lower()
    args = token.args
    kwargs = token.kwargs
    raw  = token.raw

    if _acs:
        _acs = False
        yield Token("CONTROL", text=f"{ESC}(B")

    # Palette color
    if cmd.lstrip('/') in get_current_palette():
        token.kind = "COLOR"
        token.text = get_palette_entry(cmd)
        yield token
        return

    if cmd in _runtime_vars:
        yield from _handle_var(token)
        return

    if cmd.lstrip('/') in ANSI_ATTRS:
        yield from _handle_attr(token)
        return

    if cmd in _acs_map:
        yield from _handle_acs(token)
        return

##    print(f"_handle_command.100: calling handler_dispatch {token=}")
    yield from handler_dispatch(token)
    return

    # handle runtime variables
    if cmd == "var" and args:
        yield from _handle_var(token)


    # alternate character set
    if cmd == "acs" and args:
        yield from _handle_acs(token)
        return

    # RGB
    if cmd == "rgb" and args:
        yield from _handle_rgb(token)
        return

    # F6 (hard newline)
    if cmd == "f6":
#        print(f"_handle_command.500: {token=}")
        yield from _handle_f6(token)
        return

    # reset attributes
    if cmd == "reset":
        yield from _handle_reset(token)
        return

    # CURPOS
    if cmd in ("curpos",):
        yield from _handle_curpos(token)
        return

    if cmd == "home":
        yield from _handle_home(token)

    # ERASELINE / ERASEDISPLAY
    if cmd in ("eraseline", "el"):
        mode = int(token.args[0]) if token.args else 0
        yield Token("ERASELINE", None, (mode,), False)
        return

    if cmd in ("erasedisplay", "ed"):
        yield from _handle_ed(token)
        return

    # CHA
    if cmd == "cha":
        col = int(token.args[0]) if token.args else 1
        yield Token("CHA", args=(col,))
        return

    # unknown commands
##    yield Token("UKNOWN", value=token.raw, args=(), kwargs={}, text=token.raw)


def _write_token(token: Token, flush: bool=True, stream=None):
    """
    Write a Token to stdout, interpreting commands and attributes.
    - WORD/WHITESPACE: printed directly
    - F6: hard newline
    - COMMANDS: processed via _handle_command()
    """
    global _raw, _current_output_stream, _current_output_stream_lock

    with _current_output_stream_lock:
        if type(token) == str:
            _current_output_stream.write(f"STR:{repr(token)}")
        else:
            if not _raw:
                _current_output_stream.write(str(token.text))
            else:
                buf = token.raw or token.text

                if buf is not None:
                    _current_output_stream.write(buf)

        if flush:
            _current_output_stream.flush()
    return

# ----------------------------
# echo_iter(), echo(), and echo_file()
# ----------------------------
def echo_iter(text, width=None, wordwrap=True, palette=None, vars=None, raw=False):
    """
    Generator that yields tokens for rendering.
    Handles WORD, WHITESPACE, F6 (hard newline), attributes, and commands.
    """
    global _runtime_vars, _cursor_col, _raw, _wordwrap, _previous_token
    
    _raw = raw

    if width is None:
        width = get_terminal_width()  # default or queried width
    
    palette = palette or c64_palette
    _runtime_vars = _runtime_vars or {}

    for token in tokenize(text):
        if token.kind == "COMMAND":
            yield from _handle_command(token)
        elif token.kind == "WORD": # in ("WORD", "WHITESPACE"):
#            print(f"ping")
            word_len = len(token.text)

            if _wordwrap and _cursor_col + word_len > width - 1:
                # insert hard newline before this word/space
                yield Token("F6", raw="{f6}", text="*\n")
                _cursor_col = 0

            _cursor_col += word_len
            yield token
        elif token.kind == "WHITESPACE":
            if _previous_token.kind == "F6" and token.text == " ":
                continue
            yield token
        elif token.kind == "F6":
            yield from _handle_f6(token)
        else:
            # unknown token, yield as-is
            yield token

        _previous_token = token

def echo(text, *, palette=None, width=None, wordwrap=True, raw=False, flush=True, end=""):
    """
    Print text to stdout, interpreting inline commands unless raw=True.
    width: override detected terminal width if not None
    wordwrap: enable/disable word wrapping
    raw: if True, commands are treated as literal text
    flush: if True, flush after writing
    """
    global _raw
    
    _raw = raw

    for token in echo_iter(text, width=width, wordwrap=wordwrap, raw=raw, palette=palette):
        _write_token(token, flush=flush)

    # Always write the "end" string
    if end:
        sys.stdout.write(end)
        if flush:
            sys.stdout.flush()

def echo_file(filepath, page_size=20, raw=False):
    with open(filepath, 'r') as f:
        line_count = 0
        for line in f:
            echo(line, end='', raw=raw)  # don't add extra newline
            line_count += 1
            if line_count % page_size == 0:
                input("More?")  # wait every page

# ----------------------------
# input
# ----------------------------
# internal mapping of escape sequences to key names
_input_escape_sequences = {
    f"{ESC}[A": "KEY_UP",
    f"{ESC}[B": "KEY_DOWN",
    f"{ESC}[C": "KEY_RIGHT",
    f"{ESC}[D": "KEY_LEFT",
    f"{ESC}[H": "KEY_HOME",
    f"{ESC}[F": "KEY_END",
    f"{ESC}[2~": "KEY_INSERT",
    f"{ESC}[3~": "KEY_DELETE",
    f"{ESC}[5~": "KEY_PAGEUP",
    f"{ESC}[6~": "KEY_PAGEDOWN",
    f"{ESC}OP": "KEY_F1",
    f"{ESC}OQ": "KEY_F2",
    f"{ESC}OR": "KEY_F3",
    f"{ESC}OS": "KEY_F4",
    f"{ESC}[15~": "KEY_F5",
    f"{ESC}[17~": "KEY_F6",
    f"{ESC}[18~": "KEY_F7",
    f"{ESC}[19~": "KEY_F8",
    f"{ESC}[20~": "KEY_F9",
    f"{ESC}[21~": "KEY_F10",
    f"{ESC}[23~": "KEY_F11",
    f"{ESC}[24~": "KEY_F12",
}

_input_simple_keys = {
    "\x7f": "KEY_BACKSPACE",  # typical terminal backspace
    "\b": "KEY_BACKSPACE",    # alternate backspace representation
    "\r": "KEY_ENTER",            # carriage return
    "\n": "KEY_ENTER",            # newline (for some terminals)
    "\t": "KEY_TAB",              # tab
}

def getch(timeout=None):
    """
    Return a canonical key name or None if timeout.
    Handles:
    - simple keys (backspace, enter, tab)
    - escape sequences (arrows, function keys)
    - single Escape key
    - Ctrl-C -> KeyboardInterrupt
    - Ctrl-D -> EOFError
    """
    fd = _current_input_stream.fileno()
    old_settings = termios.tcgetattr(fd)
    old_flags = None

    try:
        tty.setraw(fd)
        if platform.system() != "Darwin":
            old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            return None

        ch = _current_input_stream.read(1)

        # check for Ctrl-C / Ctrl-D
        if ch == "\x03":  # Ctrl-C
            raise KeyboardInterrupt
        if ch == "\x04":  # Ctrl-D
            raise EOFError

        # check simple keys
        if ch in _input_simple_keys:
            return _input_simple_keys[ch]

        elif ch == ESC:
            # Handle escape sequence
            seq = ''
            esc_start = time.time()

            while time.time() - esc_start < 0.5:
                rlist, _, _ = select.select([_current_input_stream], [], [], 0.01)
                print(f"{rlist=}")
                if rlist:
                    try:
                        next_ch = _current_input_stream.read(1)
                    except (IOError, OSError):
                        break
                    if not next_ch:
                        break
                    seq += next_ch
                    print(f"io.getch.100: {seq=}")
                    if seq in KEYS:
                        return KEYS[seq]
#                else:
#                    break

            if not seq:
                return "KEY_ESC"
            return "\x1B" + seq  # Raw unknown escape sequence

        # normal printable character
        return ch

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # restore original flags if changed
        if platform.system() != "Darwin" and old_flags is not None:
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

def getstr(prompt: str = "") -> str:
    """Read a string from the user with full line editing support and insert/overwrite indicator."""
    buf: list[str] = []
    cursor = 0
    insert_mode = True

    # Print the prompt
    if prompt:
        echo(prompt, end="", flush=True)

    # Save cursor position (start of input)
    echo("{decsc}", end="", flush=True)

    def update_bottombar():
        nonlocal insert_mode
        screen.setbottombar("io_demo_getstr", "[INS]" if insert_mode else "[OVR]")

    def draw_line():
        """Redraw the buffer and insert/overwrite indicator with proper cursor positioning."""
        mode = "[INS]" if insert_mode else "[OVR]"
        total_len = len(buf) + len(mode)  # full string length including indicator

        # Move to start of input
        echo("{decrc}", end="", flush=True)

        # Print the buffer
        echo("".join(buf), end="", flush=True)

        # Print insert/overwrite indicator
        echo(f" {mode}", end="", flush=True)

        # Move cursor back to logical position within buffer
        if cursor < len(buf):
            n = len(buf) - cursor
            echo(f"{{cursorleft:{n + len(mode) + 1}}}", end="", flush=True)

    draw_line()  # initial draw
    update_bottombar()

    while True:
        key = getch()
        if key is None:
            continue

        if key in ("\r", "\n", "KEY_ENTER"):
            echo("{f6}", end="", flush=True)
            return "".join(buf)

        elif key == "KEY_BACKSPACE":
            if cursor > 0:
                del buf[cursor - 1]
                cursor -= 1
                echo("{cursorleft}", end="", flush=True)
                draw_line()

#        elif key == "KEY_DC":
#            if cursor < len(buf):
#                del buf[cursor]
#                draw_line()

        elif key == "KEY_LEFT":
            if cursor > 0:
                cursor -= 1
                echo("{cursorleft}", end="", flush=True)

        elif key == "KEY_RIGHT":
            if cursor < len(buf):
                cursor += 1
                echo("{cursorright}", end="", flush=True)

        elif key == "KEY_HOME":
            if cursor > 0:
                echo(f"{{cursorleft:{cursor}}}", end="", flush=True)
                cursor = 0

        elif key == "KEY_END":
            if cursor < len(buf):
                n = len(buf) - cursor
                echo(f"{{cursorright:{n}}}", end="", flush=True)
                cursor = len(buf)

        elif key == "KEY_IC":  # Insert toggle
            insert_mode = not insert_mode
            draw_line()  # update indicator

        else:
            if insert_mode or cursor == len(buf):
                buf.insert(cursor, key)
            else:  # overwrite mode
                buf[cursor] = key
            echo(key, end="", flush=True)
            cursor += 1
#            draw_line()

# ----------------------------
# End of io.py
# ----------------------------
