import os
import sys
import tty
import time
import select
import fcntl
import termios

ESC = '\x1B'
ETX = '\x03' # ctrl-c
EOF = '\x04' # ctrl-d

# Dictionary to map ANSI escape sequences to logical key names
# This is a MINIMAL subset—a robust solution requires a much larger map.
KEY_MAP = {
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
#    f"{ESC}OP": "KEY_HELP", # PF1
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

def getch_nonblocking(timeout=3.0):
    """Reads a single keypress without blocking and handles control/extended keys."""
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    old_flags = None
    
    try:
        # 1. Set Terminal to Raw/Cbreak Mode
        tty.setraw(fd)
        
        # --- INITIAL READ SETUP ---
        # Use select to wait for the first byte with the specified timeout
        # select() will block until data is available or the timeout is reached.
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        
        if not ready:
            # Timeout occurred before the first character was available
            return None

        # 2. Set Non-Blocking I/O
        # Save old flags and set O_NONBLOCK flag on the file descriptor
        old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

        try:
            # Attempt to read a single byte
            char = os.read(fd, 1).decode()
        except BlockingIOError:
            # If nothing is available, return None immediately
            return None
        
        # 3. Handle Control Characters
        if char == "\x01":
            return "KEY_CTRL_A"
        if char == '\x03':  # Ctrl+C (ETX)
            raise KeyboardInterrupt
        if char == '\x04':  # Ctrl+D (EOT)
            raise EOFError
        if char == '\x05': # ctrl-e (EOL)
            return "KEY_CTRL_E"
        if char in ('\x7F', '\x08'):
            return "KEY_BACKSPACE"
        if char == '\r':
            return "KEY_ENTER"
        if char == '\x15': # ctrl-u
            return "KEY_CUTTOBOL"

        # 4. Handle Escape Sequences and Plain ESC
        if char == ESC: # ESCAPE byte
            sequence = char
            # Read subsequent bytes without blocking to check for a sequence
            # Wait a short period, then check up to a maximum number of bytes (e.g., 10)
            
            # The critical logic: read more bytes *until* BlockingIOError *or* 10 bytes read
            for _ in range(10): 
                try:
                    # Reading one byte at a time is safest for sequential parsing
                    next_char = os.read(fd, 1).decode()
                    sequence += next_char
                except BlockingIOError:
                    break # Sequence transmission stopped

            # A. Check for plain ESC
            if len(sequence) == 1:
                 return "KEY_ESC" # Plain ESC key was pressed (as no other bytes followed)
                 
            # B. Check for known escape sequences
            # Sort keys by length descending to match longest possible sequence first
            for code, name in sorted(KEY_MAP.items(), key=lambda item: len(item[0]), reverse=True):
                if sequence.endswith(code):
                    return name
            
            # C. Unknown escape sequence
            return f"UNKNOWN_ESC:{repr(sequence)}"

        # 5. Return a regular character
        return char
        
    finally:
        # 6. Restore Terminal Settings (CRUCIAL!)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # Restore old flags (blocking?)
        if old_flags:
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

if __name__ == "__main__":
    done = False
    while not done:
        ch = getch_nonblocking(timeout=0.01)
        if ch == "KEY_ENTER":
            break
        if ch is None:
            continue

        print(ch, end="", flush=True)
