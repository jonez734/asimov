from .common import Token
from .const import CSI, DEFAULT_PALETTE_NAME

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
