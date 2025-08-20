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
import sys
import re
from collections import namedtuple

# ----------------------------
# Token definition
# ----------------------------
Token = namedtuple("Token", ["kind", "value", "args", "kwargs", "raw"])
# kind: WORD, WHITESPACE, F6, COMMAND, ACS, etc.
# value: string content or command name
# args: positional args (list)
# kwargs: keyword args (dict)
# raw: original matched string

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
    return f"\033[{prefix};2;{r};{g};{b}m"

# ANSI palette (foreground)
ansi_palette = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    # Light colors
    "lightblack":   "\033[90m",
    "lightred":     "\033[91m",
    "lightgreen":   "\033[92m",
    "lightyellow":  "\033[93m",
    "lightblue":    "\033[94m",
    "lightmagenta": "\033[95m",
    "lightcyan":    "\033[96m",
    "lightwhite":   "\033[97m",
    # Reset
    "reset":        "\033[0m",
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
    "reset":       "\033[0m",
}

# Background aliases
def make_bg(palette):
    bg = {}
    for k, v in palette.items():
        if k != "reset":
            bg[f"bg{k}"] = v.replace("38", "48")
    return bg

c64_palette.update(make_bg(c64_palette))
ansi_palette.update(make_bg(ansi_palette))

# ----------------------------
# ACS characters
# ----------------------------
acs_map = {
    "ulcorner": "\u250C", # ┌
    "urcorner": "\u2510", # ┐
    "llcorner": "\u2514", # └
    "lrcorner": "\u2518", # ┘
    "hline":    "\u2500", # ─
    "vline":    "\u2502", # │
    "ttee":     "\u252C", # ┬
    "btee":     "\u2534", # ┴
    "ltee":     "\u251C", # ├
    "rtee":     "\u2524", # ┤
    "cross":    "\u253C", # ┼
    "dblhline": "\u2550", # ═
    "dblvline": "\u2551", # ║
    "dblul":    "\u2554", # ╔
    "dblur":    "\u2557", # ╗
    "dblll":    "\u255A", # ╚
    "dbllr":    "\u255D", # ╝
}

# ----------------------------
# Command patterns
# ----------------------------
command_patterns = [
    # name, pattern
    ("F6",       r'\{f6(?::(?P<repeat>\d+))?\}'), 
    ("RESET",    r'\{/?reset\}'), 
    ("CLS",      r'\{cls|clearscreen|erasedisplay:2\}'), 
    ("HOME",     r'\{home\}'), 
    ("CURPOS",   r'\{curpos(?::(?P<y>\d+)(,(?P<x>\d+))?)?\}'), 
    ("ERASELINE", r'\{(?:eraseline|el)(:(?P<elmode>\d))?\}'), 
    ("CHA",      r'\{cha(:(?P<chanum>\d{,3}))?\}'), 
    ("CUP",      r'\{cup|cursorup(?::(?P<n>\d+))?\}'), 
    ("CUD",      r'\{cud|cursordown(?::(?P<n>\d+))?\}'), 
    ("CUF",      r'\{cuf|cursorforward|cursorleft(?::(?P<n>\d+))?\}'), 
    ("CUB",      r'\{cub|cursorback|cursorbackward|cursorright(?::(?P<n>\d+))?\}'), 
    ("STBM",     r'\{decstbm(?::(?P<top>\d+),(?P<bottom>\d+))?\}'), 
    ("RGB",      r'\{rgb(?::(?P<fgbg>fg|bg))?:(?P<spec>[#\d,]+)\}'), 
    ("VAR",      r'\{var:(?P<name>\w+)\}'), 
    ("ACS",      r'\{acs:(?P<name>\w+)(:(?P<repeat>\d+))?\}'), 
]

# ----------------------------
# Aliases / command expansion
# ----------------------------
command_aliases = {
    "cls": "{erasedisplay:2}{home}",
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

# ----------------------------
# Tokenizer
# ----------------------------
def tokenize(text):
    """Yields Token(kind, value, args, kwargs, raw)"""
    pos = 0
    while pos < len(text):
        m = None
        for name, pattern in command_patterns:
            m = re.match(pattern, text[pos:], re.IGNORECASE)
            if m:
                kwargs = {k: v for k, v in m.groupdict().items() if v is not None}
                yield Token("COMMAND", name.lower(), [], kwargs, m.group(0))
                pos += m.end()
                break
        if m:
            continue
        if text[pos].isspace():
            yield Token("WHITESPACE", text[pos], [], {}, text[pos])
        else:
            # WORD: span until next whitespace or command
            end = pos + 1
            while end < len(text) and not text[end].isspace() and text[end] != "{":
                end += 1
            yield Token("WORD", text[pos:end], [], {}, text[pos:end])
            pos = end - 1
        pos += 1

# ----------------------------
# Process commands
# ----------------------------
def process_command(token, palette, variables):
    """Returns a string to output for a single command Token"""
    name = token.value
    kwargs = token.kwargs
    # aliases
    if name in command_aliases:
        expanded = command_aliases[name]
        # recursively tokenize and process
        return "".join(process_command(t, palette, variables) 
                       for t in tokenize(expanded))
    elif name == "reset":
        return palette.get("reset", "\033[0m")
    elif name == "f6":
        repeat = int(kwargs.get("repeat", "1"))
        return "\n" * repeat
    elif name == "rgb":
        spec = kwargs.get("spec")
        fgbg = kwargs.get("fgbg", "fg")
        prefix = 38 if fgbg.lower() == "fg" else 48
        return rgb(prefix, spec)
    elif name == "var":
        varname = kwargs.get("name")
        return str(variables.get(varname, ""))
    elif name == "acs":
        acsname = kwargs.get("name")
        repeat = int(kwargs.get("repeat", "1"))
        return acs_map.get(acsname, "?") * repeat
    # Cursor/erase commands (simplified)
    elif name == "home" or name == "curpos":
        y = kwargs.get("y", "1")
        x = kwargs.get("x", "1")
        return f"\033[{y};{x}H"
    elif name == "ed" or name == "erasedisplay":
        mode = kwargs.get("elmode", "0")
        return f"\033[{mode}J"
    elif name == "el" or name == "eraseline":
        mode = kwargs.get("elmode", "0")
        return f"\033[{mode}K"
    elif name == "cup":
        n = int(kwargs.get("n", "1"))
        return f"\033[{n}A"
    elif name == "cud":
        n = int(kwargs.get("n", "1"))
        return f"\033[{n}B"
    elif name == "cuf":
        n = int(kwargs.get("n", "1"))
        return f"\033[{n}C"
    elif name == "cub":
        n = int(kwargs.get("n", "1"))
        return f"\033[{n}D"
    elif name == "decstbm" or name == "stbm":
        top = int(kwargs.get("top", "1"))
        bottom = int(kwargs.get("bottom", get_terminal_size()[1]))
        return f"\033[{top};{bottom}r"
    return ""  # unknown command

current_palette = c64_palette.copy()

def set_palette(palette_name):
    global current_palette
    if palette_name.lower() == "c64":
        current_palette = c64_palette.copy()
    elif palette_name.lower() == "ansi":
        current_palette = ansi_palette.copy()
    else:
        raise ValueError(f"Unknown palette: {palette_name}")

# ----------------------------
# echo() and echo_file()
# ----------------------------
def echo(text, palette=None, variables=None, end="\n", raw=False):
    """Echo text, interpreting commands unless raw=True"""
    if palette is None:
        palette = current_palette
    if variables is None:
        variables = {}
    if raw:
        print(text, end=end)
        return
    out = []
    for token in tokenize(text):
        if token.kind == "WORD" or token.kind == "WHITESPACE":
            out.append(token.value)
        elif token.kind == "COMMAND":
            out.append(process_command(token, palette, variables))
    print("".join(out), end=end)

def echo_file(filepath, palette=None, variables=None, more_prompt="--more--"):
    """Echo file line by line with optional more prompt and commands"""
    if palette is None:
        palette = current_palette
    if variables is None:
        variables = {}
    with open(filepath, "r") as f:
        for line in f:
            echo(line.rstrip("\n"), palette=palette, variables=variables)
            input(process_command(Token("COMMAND", "var", [], {"name":"more_prompt"}, ""), palette, variables) or more_prompt)

# ----------------------------
# End of io.py
# ----------------------------
