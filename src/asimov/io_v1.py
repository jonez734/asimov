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
import threading
import collections

import tty
import termios # get_cursor_position()



##from bbsengine6 import screen

DEFAULT_PALETTE_NAME = "c64"

ESC   = "\x1B"
#CSI   = "\x9B"
CSI   = f"{ESC}["
BEL  = "\007"

_current_input_stream = sys.stdin

_current_output_stream = sys.stdout

_current_stream_lock = threading.Lock()

def set_output_stream(stream):
    global _current_output_stream
    _current_output_stream = stream

def set_input_stream(stream):
    global _current_input_stream
    _current_input_stream = stream

def _write_current_output_stream(s:str, flush=False):
    _current_output_stream.write(s)
    if flush:
        _current_output_stream.flush()

def write_current_output_stream(s:str, flush=False):
    with _current_stream_lock:
        return _write_current_output_stream(s, flush=flush)

_input_queue = collections.deque()

def _read_current_input_stream(size:int=1) -> str:
    if _input_queue:
        return _input_queue.popleft()
    return _current_input_stream.read(size)

def read_current_input_stream(size:int=1) -> str:
    with _current_stream_lock:
        return _read_current_input_stream(size)

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

# Assuming _current_input_stream and _current_input_stream are defined globally/passed
# Using sys.stdin for example, but your usage of _current_input_stream is correct.

def _read_terminal_response(terminator: str, timeout: float = 1.0) -> str | None:
    """
    Reads characters from the terminal until the specified terminator is received
    or the timeout expires, using a non-blocking select loop.
    """
    fd = _current_input_stream.fileno()

    # 1. Save and set terminal mode
    old_settings = termios.tcgetattr(fd)
    try:
        # Set to cbreak mode (raw-like, but includes signal processing)
        tty.setcbreak(fd) 

        response = ""
        for _ in range(10):
            ch = os.read(fd, 1).decode(_current_input_stream.encoding)
            response += ch
            if ch == terminator:
                return response
    finally:
        # 3. Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def drain_stream_to_queue(stream, queue):
    """
    Read all available characters from `stream` and append them to `queue`.
    Stops when the stream would block.
    Works with stdin, stdout, or any file-like object with .fileno().
    """
    fd = stream.fileno()

    # Save current flags
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    try:
        # Set non-blocking
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        while True:
            try:
                print("\x07", flush=True, end="")
                ch = stream.read(1)
                if not ch:
                    break  # EOF or no more data
                queue.append(ch)
            except BlockingIOError:
                break  # would block → stop
    finally:
        # Restore original flags
        fcntl.fcntl(fd, fcntl.F_SETFL, fl)

# Regex for DSR reply: ESC [ <row> ; <col> R
DSR_CURPOS_RE = re.compile(r'\x1b\[(\d+);(\d+)R')

def get_dsr(mode="curpos", timeout: float = 1.0) -> str:
    """
    Query the terminal for cursor position (DSR) and return the response string.
    
    Sends ESC[6n and reads raw bytes until the terminating 'R' is received.
    Uses the global _current_stream_lock to prevent interleaved output.
    
    Args:
        timeout: Optional timeout in seconds for the DSR response.
    
    Returns:
        Decoded response string, e.g., '\x1b[12;40R'.
    
    Raises:
        TimeoutError if no complete response is received in time.
    """

    if mode == "curpos":
        code = "6"
    elif mode == "status":
        code = "5"
    else:
        raise ValueError

    with _current_stream_lock:
        # drain input and output into queues
        drain_stream_to_queue(_current_input_stream, _input_queue)
##        drain_stream_to_queue(_current_output_stream, _output_queue)

        # store original settings
        fd = _current_input_stream.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            # Step 0: set raw mode
            tty.setraw(fd) # _current_input_stream
            # Step 1: send the DSR request
            _write_current_output_stream(f"{ESC}[{code}n", flush=True)

            # Step 2: read the response in a loop until we see the trailing 'R'
            start_time = time.time()
            buffer = ""

            while True:
                # Step 2a: read up to 32 bytes (adjust as needed)
                chunk = _read_current_input_stream(1)
                buffer += chunk

                match = DSR_CURPOS_RE.search(buffer)
                if match:
                    row, col = map(int, match.groups())

                    # Remove the matched DSR from buf and push the rest back into the queue
                    start, end = match.span()
                    leftover = buffer[:start] + buffer[end:]
                    _input_queue.clear()
                    _input_queue.extend(leftover)
                    return (row, col)

                # Step 2c: check for timeout
                if (time.time() - start_time) > timeout:
                    raise TimeoutError(f"DSR response not received in {timeout}s: {buffer!r}")
                    break

            return buffer # .decode(errors="ignore")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # restore

##    write_current_output_stream(f"{CSI}{code}n", flush=True)
##    _current_output_stream.flush()
##    return _read_terminal_response(terminator)

def get_cursor_position(timeout: float = 1.0):
    """
    Return the current cursor position as (row, col) integers.

    Args:
        timeout: Optional timeout in seconds for DSR response.

    Returns:
        Tuple (row, col) of cursor position (1-based).

    Raises:
        ValueError if the response cannot be parsed.
        TimeoutError if no response is received in time.
    """
    return get_dsr("curpos", timeout=timeout)

##    # Expect something like: ESC [ row ; col R
##    if not resp.startswith(CSI) or not resp.endswith("R"):
##        raise ValueError(f"Unexpected DSR response: {resp!r}")
##
##    try:
##        body = resp[2:-1]   # strip ESC[ and trailing R
##        row_str, col_str = body.split(";")
##        return int(row_str), int(col_str)
##    except Exception as e:
##        raise ValueError(f"Failed to parse DSR response: {resp!r}") from e

def get_terminal_status():
    """Device Status (DECTST / terminal readiness)

    Query: ESC [ 5 n

    Response: ESC [ 0 n → OK, ESC [ 3 n → error
"""

    with _current_stream_lock:
        response = get_dsr("status")
        if response and response.startswith(CSI) and response.endswith("n"):
            part = int(response[2])
            if part == 0:
                return True
            elif part == 3:
                return False
            else:
                return None
    
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

    if _acs:
        _acs = False
        token.text = f"{ESC}(B"
        yield token

    # Palette color
    if cmd.lstrip('/') in get_current_palette():
##        token.kind = "COLOR"
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

    # reset attributes
    if cmd == "reset":
        yield from _handle_reset(token)
        return

    # CURPOS
    if cmd == "curpos":
        yield from _handle_curpos(token)
        return

    if cmd == "home":
        yield from _handle_home(token)
        return

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
#        setbottombar("io_demo_getstr", "[INS]" if insert_mode else "[OVR]")

    def draw_line():
        """Redraw the buffer and insert/overwrite indicator with proper cursor positioning."""
        mode = "[INS]" if insert_mode else "[OVR]"

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
