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

## from collections import namedtuple
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterator

DEFAULT_PALETTE_NAME = "c64"

CSI   = "\x9B" # 8-bit equiv of ESC[
ESC   = "\x1B" # ESC[ is used by 7-bit terminals
BELL  = "\007"

# ----------------------------
# Token definition
# ----------------------------

# kind: WORD, WHITESPACE, F6, COMMAND, ACS, COLOR
# value: string content or command name
# args: positional args (list)
# kwargs: keyword args (dict)
# raw: original matched string

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
    result = f"\033[{prefix};2;{r};{g};{b}m"
##    print(f"rgb.100: {result=}")
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
    "black":   f"{ESC}[30m",
    "red":     f"{ESC}[31m",
    "green":   f"{ESC}[32m",
    "yellow":  f"{ESC}[33m",
    "blue":    f"{ESC}[34m",
    "magenta": f"{ESC}[35m",
    "cyan":    f"{ESC}[36m",
    "white":   f"{ESC}[37m",
    # Light colors
    "lightblack":   f"{ESC}[90m",
    "lightred":     f"{ESC}[91m",
    "lightgreen":   f"{ESC}[92m",
    "lightyellow":  f"{ESC}[93m",
    "lightblue":    f"{ESC}[94m",
    "lightmagenta": f"{ESC}[95m",
    "lightcyan":    f"{ESC}[96m",
    "lightwhite":   f"{ESC}[97m",
    # Reset
    "reset":        f"{ESC}[0m",
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
    "reset":       f"{ESC}[0m",
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
acs_map = {
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
    ("cup", r'cup|cursorup'),
    ("cud", r'cud|cursordown'),
    ("cuf", r'cuf|cursorforward|cursorleft'),
    ("cub", r'cub|cursorright|cursorback|cursorbackward'),
    ("acs", r'acs'),
    ("f6",  r'f6'),

    # runtime variables
    ("var", r'var'),
}
_compiled_command_handlers = [(kind, re.compile(pattern, re.IGNORECASE)) for kind, pattern in _command_handlers]

_whitespace_re = re.compile(r'(\s+)')
_word_re = re.compile(r'[^\s{}]+')
_command_re = re.compile(r"""
    \{
    (?P<name>[a-zA-Z_][a-zA-Z0-9_-]*)  # command name: first char letter/_ , rest letters/digits/_/-
    (?:                                # optional args block
        [:,]                           # args sep "," or ":"
        (?P<params>[^}]*)              # everything up to the closing brace
    )?
    \}
""", re.VERBOSE | re.IGNORECASE)

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

    try:
        sys.stdout.write(f"{ESC}[{code}n")
        sys.stdout.flush()
        return _read_terminal_response(terminator)
    finally:
        pass

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
    if response and response.startswith(f"{ESC}[") and response.endswith("R"):
        parts = response[2:-1].split(";")
        row, col = int(parts[0]), int(parts[1])
        return row, col

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write(f"{ESC}[0n")  # DSR to query status
        sys.stdout.flush()

        # Read response ESC [ row ; col R
        response = read_terminal_response("R")
        if response.startswith(f"{ESC}[") and response.endswith("n"):
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
            tok = Token(
                kind="WHITESPACE",
                value=m.group(1),       # optional semantic info
                repeat=len(m.group(0)), # total length of run
                text=None,              # to be filled by handler
                raw=m.group(0)
            )
##            print(f"tokenize.100: {tok=}")
            yield from _handle_whitespace(tok)
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
        yield Token("WORD", value=run, text=run)
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
    if run == "\n":
        token.kind = "F6"
        token.repeat = 1
        token.text = "\n"
        yield token
        return

    i = 0
    while i < len(run):
        ch = run[i]
        count = 1
        while i + count < len(run) and run[i + count] == ch:
            count += 1
        yield Token(
            kind="WHITESPACE",
            value=ch,           # the character itself (' ', '\t', or '\n')
            repeat=count,       # how many times it repeats
            text=ch * count,    # string that will be written
            raw=ch * count
        )
        i += count

def _handle_acs(token):
    name = token.args[0]
    repeat = int(token.args[1]) if len(token.args) > 1 else 1
##    print(f"_handle_acs.100: {name=} {repeat=}")
    char = acs_map.get(name, "?")
##    print(f"_handle_acs.120: {token=} {char=}")
    # Yield a single ACS token with repeat in kwargs
    token.text = char * repeat
    token.kind = "ACS"
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
    y = int(token.args[0]) if token.args else 1
    x = int(token.args[1]) if len(token.args) > 1 else 1
    print("curpos")
    token.text = f"{ESC}[{y};{x}H"
    yield token
    
def _handle_f6(token):
    repeat = int(token.args[0]) if token.args else 1
##    print(f"_handle_f6.100: {token.args=} {repeat=}")
    token.repeat = repeat
    token.text = "\n"*repeat
    token.kind = "F6"
    yield token
    return

def _handle_home(token):
    token.text = f"{ESC}[H"
    yield token
    return

def _handle_ed(token):
    mode = int(token.args[0]) if token.args else 0
    yield Token("ERASEDISPLAY", args=(mode,), text=f"{ESC}[")

def _handle_cuu(token):
    repeat = token.args[0] or 1
    token.kind = "CURSOR"
    token.repeat = repeat
    token.text = f"{ESC}[{repeat}A"
    yield token

def _handle_cud(token):
    repeat = token.args[0] or 1
    token.kind = "CURSOR"
    token.repeat = repeat
    token.text = f"{ESC}[{repeat}B"
    yield token

def _handle_cuf(token):
    repeat = int(token.args[0]) or 1
    token.kind = "CURSOR"
    token.repeat = repeat
    token.text = f"{ESC}[{repeat}C"
    yield token

def _handle_cub(token):
    repeat = int(token.args[0]) or 1
    token.kind = "CURSOR"
    token.repeat = repeat
    token.text = f"{ESC}[{repeat}D"
    yield token

# save/restore terminal attributes
@dataclass
class TerminalState():
    cursor_row = 1
    cursor_col = 1
    wordwrap  = True

_terminal_states = []
_wordwrap = True

def _handle_decsc(token):
    (row, col) = get_cursor_position()
    state = TerminalState()
    state.cursor_row = row
    state.cursor_col = col
    state.wordwrap = _wordwrap
    _terminal_states.append(state)

def _handle_decrc(token):
    state = _terminal_states.pop()
    yield Token("CURPOS", args=(state.cursor_row, state.cursor_col), raw=token.raw, text=f"{ESC}[{row};{col}H")
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

##    print(f"handler_dispatch.100: {token=}")

    cmd = token.value.lower()

    for kind, regex in _compiled_command_handlers:
##        print(f"handler_dispatch.140: {cmd=}")
        if regex.fullmatch(cmd):
            handler_name = f"_handle_{cmd}"
##            print(f"handler_dispatch.160: {handler_name=}")
            handler = globals().get(handler_name)
            if callable(handler):
#                print(f"handler_dispatch.140: {handler=}")
#                token.kind = token.value
#                print(f"handler_dispatch.120: {token=}")
                # yield from the generator
                yield from handler(token)
                return True
            break
    # fallback
#    yield from _handle_unknown(token)
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

##    print(f"_handle_command.100: calling handler_dispatch {token=}")
    yield from handler_dispatch(token)
    return

    # save/restore cursor position, wordwrap bool
    if cmd == "decsc" and not args:
        _handle_decsc(token)
        return

    if cmd == "decrc" and not args:
        _handle_decrc(token)
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
        _handle_reset(token)
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

    # cursor movements
    if cmd in ("cup", "cursorup"):
        n = int(token.args[0]) if token.args else 1
        yield Token("CUP", None, (n,), False)
        return

    if cmd in ("cud", "cursordown"):
        n = int(token.args[0]) if token.args else 1
        yield Token("CUD", None, (n,), False)
        return

    if cmd in ("cuf", "cursorforward", "cursorright"):
        yield from _handle_cuf(token)
#        n = int(token.args[0]) if token.args else 1
#        yield Token("CUF", None, (n,), False)
        return

    if cmd in ("cub", "cursorback", "cursorbackward", "cursorleft"):
        n = int(token.args[0]) if token.args else 1
        yield Token("CUB", None, (n,), False)
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
    if stream is None:
        stream = sys.stdout

#    stream.write(str(token))
#    text = token.text or token.value or "??"
    stream.write(str(token.text))
    if flush:
        stream.flush()

# ----------------------------
# echo() and echo_file()
# ----------------------------
def echo_iter(text, width=None, wordwrap=True, palette=None, vars=None, raw=False):
    """
    Generator that yields tokens for rendering.
    Handles WORD, WHITESPACE, F6 (hard newline), attributes, and commands.
    """
    global _runtime_vars

    if width is None:
        width = get_terminal_width()  # default or queried width
    palette = palette or c64_palette
    _runtime_vars = _runtime_vars or {}

    x = 0  # current horizontal position
    for tok in tokenize(text):
##        print(f"echo_iter.100: {tok=}")
        if tok.kind == "COMMAND":
            if raw:
                yield tok.raw
                continue
            yield from _handle_command(tok)

        elif tok.kind == "F6":
            repeat = tok.args[0] if tok.args else 1
            yield Token(kind=tok.kind, text="\n"*int(repeat))
            x = 0

        elif tok.kind in ("WORD", "WHITESPACE"):
            word_len = len(tok.value)
            
            if wordwrap and x + word_len > width:
                # insert hard newline before this word/space
                yield Token(kind="F6", value="{f6}", args=[1], raw="{f6}", text="\n")
                x = 0
            x += word_len
            yield tok

        elif tok.kind == "COMMAND":
            yield from _handle_command(tok)
            # handle F6 separately
            print(f"echo_iter.100: {tok.value=}")
            if tok.value.lower().startswith("{f6"):
                yield Token(kind="F6", value="{f6}", args=[repeat], raw=tok.raw, text="\n"*int(repeat), repeat=repeat)
                x = 0
            else:
                # all other commands yield as-is
                # recursive expansion for aliases/compound commands
                for sub_tok in _handle_command(tok, palette=palette, vars=vars):
                    yield sub_tok
                # update x if command affects cursor horizontally
                if tok.value.lower().startswith("{cha") or tok.value.lower().startswith("{curpos"):
                    # simple heuristic: reset x if absolute positioning
                    x = 0
        else:
            # unknown token, yield as-is
            yield tok

def echo(text, *, palette=None, width=None, wordwrap=True, raw=False, flush=True, end=""):
    """
    Print text to stdout, interpreting inline commands unless raw=True.
    width: override detected terminal width if not None
    wordwrap: enable/disable line wrapping
    raw: if True, commands are treated as literal text
    flush: if True, flush after writing
    """
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
