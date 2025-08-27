"""
io.py – enhanced terminal output with commands, colors, word wrap, runtime variables, ACS chars, and paging.

Features:
- echo() and echo_file() with wordwrap, raw mode, and recursive command evaluation
- ANSI and C64 palettes (foreground/background)
- RGB color support with #RRGGBB or 255,255,255
- Cursor control: CURPOS, CUP, CUD, CUF, CUB, HOME
- Clear/erase: CLS (clear+home), ERASELINE, ERASEDISPLAY
- Scroll region: DECSTBM / STBM
- ACS characters with optional repeat
- Runtime variables: {var:<name>} or {<name>}
- Markdown-style underline (**text**)
- Hard newline {f6}
- Recursive command expansion and aliases
"""

import os
import re
import sys
import time
import select

import tty, termios # get_cursor_position()

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterator

DEFAULT_PALETTE_NAME = "c64"

ESC   = "\x1B"
CSI   = "\x9B" # use {ESC}[ for 7-bit version
BELL  = "\007"

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
    def __str__(self):
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

def set_var(name, value):
    """Set a runtime variable for use in {var:<name>} or {<name>} commands."""
    _runtime_vars[name] = value

def get_var(name, default=None):
    return _runtime_vars.get(name, default)

_current_stream = sys.stdout
def set_stream(stream):
    global _current_stream
    _current_stream = stream

# ----------------------------
# ANSI / C64 color palettes
# ----------------------------
def rgb(prefix, spec):
    """Return ANSI SGR sequence for foreground (38) or background (48). Spec can be #RRGGBB or r,g,b"""
    if isinstance(spec, str) and spec.startswith("#") and len(spec) == 7:
        r, g, b = int(spec[1:3], 16), int(spec[3:5], 16), int(spec[5:7], 16)
    elif isinstance(spec, str) and "," in spec:
        r, g, b = [int(x) for x in spec.split(",")]
    else:
        raise ValueError(f"Invalid RGB spec: {spec}")
    result = f"{CSI}{prefix};2;{r};{g};{b}m"
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

def _parse_acs(args:str):
    pass

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
    "reset":        f"{CSI}0m",
}

# C64 palette
c64_palette = {
    "black":       rgb(38, "0,0,0"),
    "white":       rgb(38, "255,255,255"),
    "red":         rgb(38, "136,0,0"),
    "cyan":        rgb(38, "170,255,238"),
    "purple":      rgb(38, "204,68,204"),
    "green":       rgb(38, "0,204,85"),
    "blue":        rgb(38, "0,0,170"),
    "yellow":      rgb(38, "238,238,119"),
    "orange":      rgb(38, "221,136,85"),
    "brown":       rgb(38, "102,68,0"),
    "lightred":    rgb(38, "255,119,119"),
    "lightcyan":   rgb(38, "51,255,255"),
    "lightpurple": rgb(38, "255,119,255"),
    "lightgreen":  rgb(38, "170,255,102"),
    "lightblue":   rgb(38, "0,136,255"),
    "lightgray":   rgb(38, "187,187,187"),
    "reset":       f"{CSI}0m",
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
        if k != "reset":
            bg[f"bg{k}"] = v.replace("38", "48")
    return bg

c64_palette.update(make_bg(c64_palette))
ansi_palette.update(make_bg(ansi_palette))

_current_palette = get_palette(DEFAULT_PALETTE_NAME).copy()

# ----------------------------
# ACS characters
# ----------------------------
_acs_map = {
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
    ("cuu",    r'cup|cuu|cursorup'),
    ("cud",    r'cud|cursordown'),
    ("cuf",    r'cuf|cursorforward|cursorleft'),
    ("cub",    r'cub|cursorright|cursorback|cursorbackward'),
    ("curpos", r'curpos'),

    ("decsc",  r'decsc|savecursor'),
    ("decrc",  r'decrc|restorecursor'),

    ("decstbm", r'decstbm'),

    ("acs", r'acs'),
    ("f6",  r'f6'),

    # runtime variables
    ("var", r'var'),
    ("attr", r'attr'),
}

_compiled_command_handlers = [(kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in _command_handlers]

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

# ----------------------------
# Aliases / command expansion
# ----------------------------
command_aliases = {
    "cls": "{erasedisplay:2}{home}",
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
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)  # set raw/cbreak mode to read characters immediately
        response = ""
        while True:
            ch = sys.stdin.read(1)
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
    if response and response.startswith(f"{CSI}") and response.endswith("R"):
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
    fd = sys.stdin.fileno()
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
    token.text = token.value
    token.raw = token.value
    token.repeat = 1
    
    yield token

def _handle_whitespace(token):
    """
    Consolidate repeated whitespace characters into tokens.
    For example, a run of 3 newlines becomes:
        Token(kind="WHITESPACE", value="\n", repeat=3, text="\n\n\n")
    """
    run = token.value
#    if run == "\n":
#        token.kind = "WHITESPACE"
#        token.text = ""
#        token.repeat = 1
#        yield token
#        return

    i = 0
    while i < len(run):
        ch = run[i]
        repeat = 1
        while i + repeat < len(run) and run[i + repeat] == ch:
            repeat += 1
        yield Token(
            kind="WHITESPACE",
            value=ch,           # the character itself (' ', '\t', or '\n')
            repeat=repeat,       # how many times it repeats
            text=ch * repeat,    # string that will be written
            raw=ch * repeat
        )
        i += repeat

def _handle_acs(token):
##    print(f"_handle_acs.200: {token=}")
    if token.value == "acs":
        name = token.args[0]
        repeat = int(token.args[1]) if len(token.args) > 1 else 1
    else:
        token.value in _acs_map
        name = token.value
        repeat = int(token.args[0]) if token.args else 1

    token.kind = "ACS"
    token.text = _acs_map.get(name, "?")*repeat
    yield token
    return

    yield Token(
        kind="ACS",
        value=char,
        args=[],
        kwargs={"repeat": repeat},
        raw=token.raw,
        text=char * repeat
    )

def _handle_var(token):
##    print(f"_handle_var.100: {token=}")
    var_name = token.args[0] if token.args else token.value
    var_val = _runtime_vars.get(var_name, "")
    # recursively tokenize the value of the variable
    for t in tokenize(var_val):
        yield t
    return

def _handle_rgb(token):
    spec = token.args[-1]  # last argument is color spec
    fgbg = token.args[0] if len(token.args) > 1 else "fg"
    token.text = rgb(fgbg, spec)
    token.kind = "COLOR"
    yield token
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
    repeat = int(token.args[0]) if token.args else 1
##    print(f"_handle_f6.100: {token.args=} {repeat=}")
    token.repeat = repeat
    token.text = "\n"*repeat
    token.kind = "F6"
    yield token
    return

def _handle_home(token):
    token.text = f"{CSI}H"
    yield token
    return

def _handle_ed(token):
    mode = int(token.args[0]) if token.args else 0
    yield Token("ERASEDISPLAY", args=(mode,), text=f"erasedisplay")

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
    t = token.args[0]
    b = token.args[1]
    token.repeat = 1
    token.text = f"{CSI}{t};{b}r"
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
    

# save/restore cursor attributes
@dataclass
class TerminalState():
    cursor_row = 1
    cursor_col = 1
    wordwrap  = True
    has_color = True
    hidden = False

_terminal_states = []
_wordwrap = True
_color = True
_acs = False
_cursor_row = 1
_cursor_col = 1

def _handle_decsc(token):
    (row, col) = get_cursor_position()
##    print(f"_handle_decsc.100: {token=}")
    state = TerminalState()
    state.cursor_row = row
    state.cursor_col = col
    state.wordwrap = _wordwrap
    state.color = _color
    _terminal_states.append(state)
    return iter(())

def _handle_decrc(token):
    state = _terminal_states.pop()
    yield Token("CURPOS", args=(state.cursor_row, state.cursor_col), raw=token.raw, text=f"{CSI}{state.cursor_row};{state.cursor_col}H")
    yield Token("WORDWRAP", raw=token.raw, text=f"[WORDWRAP: {_wordwrap}]")

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
            handler_name = f"_handle_{cmd}"
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

    # command name is lowercase
    cmd = token.value.lower()
    args = token.args
    kwargs = token.kwargs
    raw  = token.raw

    # Palette color
    if cmd in get_current_palette():
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
    global _raw

    if stream is None:
        stream = sys.stdout

    if type(token) == str:
        stream.write(f"STR:{repr(token)}")
    else:
        if not _raw:
            stream.write(str(token.text))
        else:
            stream.write(str(token.raw))

    if flush:
        stream.flush()
    return

# ----------------------------
# echo() and echo_file()
# ----------------------------
def echo_iter(text, width=None, wordwrap=True, palette=None, vars=None, raw=False):
    """
    Generator that yields tokens for rendering.
    Handles WORD, WHITESPACE, F6 (hard newline), attributes, and commands.
    """
    global _runtime_vars, _cursor_col, _raw, _wordwrap
    
    _raw = raw

    if width is None:
        width = get_terminal_width()  # default or queried width
    
    width = 80

    palette = palette or c64_palette
    _runtime_vars = _runtime_vars or {}

##    x = 0  # current horizontal position
    for token in tokenize(text):
#        print(f"echo_iter.100: {token=}")
        if token.kind == "COMMAND":
##            if raw:
##                yield token
##                continue
            yield from _handle_command(token)
        elif token.kind in ("WORD", "WHITESPACE"):
#            print(f"ping")
            word_len = len(token.text)

            if _wordwrap and _cursor_col + word_len > width - 2:
                # insert hard newline before this word/space
                print(f"({_cursor_col})", end="")
                yield Token("F6", raw="{f6}", text="*\n")
                _cursor_col = 0
            _cursor_col += word_len
            yield token
        elif token.kind == "F6":
            _cursor_col = 0

        else:
            # unknown token, yield as-is
            yield token

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
# End of io.py
# ----------------------------
