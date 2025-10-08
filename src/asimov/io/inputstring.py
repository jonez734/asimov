from asimov.io.echo import echo
from asimov.io.getch import getch_str as getch
from asimov.io.common import  get_cursor_position, _current_stream_lock, _cursor_row, _cursor_col
from asimov.io.util import setbottombar, screen_init, terminal_lines
from asimov.util import logentry

# --- 1. Global Key Actions Dictionary ---
# This dict stores the key_string: lambda mapping
KEY_ACTIONS = {}

def add_key_mapping(key_string, action_lambda):
    """Adds or updates a key mapping."""
    KEY_ACTIONS[key_string] = action_lambda

def remove_key_mapping(key_string):
    """Removes a key mapping."""
    if key_string in KEY_ACTIONS:
        del KEY_ACTIONS[key_string]

# --- 2. Helper Functions (State Logic) ---

# All helpers MUST accept (buffer, curpos, scroll_offset, max_width) and return the updated tuple.
# max_width is included here because 'handle_end' and scrolling logic may depend on it.

def handle_left(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        curpos -= 1
    return buffer, curpos, scroll_offset

def handle_right(buffer, curpos, scroll_offset, max_width):
    if curpos < len(buffer):
        curpos += 1
    else:
        echo(f"{{bell}}")
    return buffer, curpos, scroll_offset

def handle_home(buffer, curpos, scroll_offset, max_width):
    # Home resets cursor and scroll offset
    return buffer, 0, 0

def handle_end(buffer, curpos, scroll_offset, max_width):
    # End moves cursor to the end of the buffer
    curpos = len(buffer)
    # Scrolling logic adjustment will be handled *after* the action in the main loop
    return buffer, curpos, scroll_offset

def handle_backspace(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        buffer = buffer[:curpos-1] + buffer[curpos:]
        curpos -= 1
    else:
        echo(f"{{bell}}")
    return buffer, curpos, scroll_offset

def handle_cuttobol(buffer, curpos, scroll_offset, max_width):
    # Keeps text *after* the cursor, resets cursor/scroll
    # 1. Store the part of the string *after* the cursor (the part we keep)
    kept_suffix = buffer[curpos:]

    # 2. Reset the buffer to only contain the kept suffix (erasing everything from 0 to curpos)
    buffer = kept_suffix

    # 3. Reset the cursor position to the new beginning of the buffer
    curpos = 0

    # 4. Adjust scroll offset if necessary (usually resetting to 0)
    scroll_offset = 0

    return buffer, curpos, scroll_offset

def handle_backspace(buffer, curpos, scroll_offset, max_width):
    if curpos > 0:
        # Delete character before the cursor
        buffer = buffer[:curpos-1] + buffer[curpos:]
        curpos -= 1
    else:
        echo("{bell}", end="", flush=True)
    return buffer, curpos, scroll_offset

# --- Helper Function for ^Y ---
def handle_yank(buffer, curpos, scroll_offset, max_width):
    global YANK_BUFFER
    yank_text = YANK_BUFFER

    # 1. Insert the yanked text at the cursor position
    buffer = buffer[:curpos] + yank_text + buffer[curpos:]

    # 2. Move the cursor past the inserted text
    curpos += len(yank_text)

    # Scroll offset adjustment will be handled by the main loop's scrolling logic
    return buffer, curpos, scroll_offset

def handle_help(buffer, curpos, scroll_offset, max_width):
    logentry("handle_help.100: trace")
    return buffer, curpos, scroll_offset

def handle_tab(buffer, curpos, scroll_offset, max_width, matches=[]):
##    matches = completer(buffer, curpos)
    if not matches:
        return buffer, curpos, scroll_offset

    prefix, word_start, word_end = get_current_word(buffer, curpos)

    if len(matches) == 1:
        # Only one match → complete directly
        word = matches[0]
        buffer = buffer[:word_start] + word + buffer[word_end:]
        curpos = word_start + len(word)
        redraw_line(prompt, buffer, max_len, start_row, start_col, curpos)
        tab_count = 0
        last_matches = []
    else:
        if matches == last_matches:
            # second tab press → show all matches
            echo("\n")
            print_matches(matches)
            redraw_line(prompt, buffer, max_len, start_row, start_col, curpos)
            tab_count = 0
        else:
            # first tab press → insert longest common prefix
            lcp = common_prefix(matches)
            if lcp and lcp != prefix:
                buffer = buffer[:word_start] + lcp + buffer[word_end:]
                curpos = word_start + len(lcp)
                redraw_line(prompt, buffer, max_len, start_row, start_col, curpos)
            last_matches = matches
            tab_count = 1

    return buffer, curpos, scroll_offset

# --- 3. Initial Mapping Setup ---
# Map the initial key actions using the management function
add_key_mapping("KEY_LEFT",      lambda b, cp, so, mw: handle_left(b, cp, so, mw))
add_key_mapping("KEY_RIGHT",     lambda b, cp, so, mw: handle_right(b, cp, so, mw))
add_key_mapping("KEY_HOME",      lambda b, cp, so, mw: handle_home(b, cp, so, mw))
add_key_mapping("KEY_CTRL_A",    lambda b, cp, so, mw: handle_home(b, cp, so, mw))
add_key_mapping("KEY_END",       lambda b, cp, so, mw: handle_end(b, cp, so, mw))
add_key_mapping("KEY_CTRL_E",    lambda b, cp, so, mw: handle_end(b, cp, so, mw))
add_key_mapping("KEY_BACKSPACE", lambda b, cp, so, mw: handle_backspace(b, cp, so, mw))
add_key_mapping("KEY_CUTTOBOL",  lambda b, cp, so, mw: handle_cuttobol(b, cp, so, mw))
add_key_mapping("KEY_YANK",      lambda b, cp, so, mw: handle_yank(b, cp, so, mw))
add_key_mapping("KEY_F1",        lambda b, cp, so, mw: handle_help(b, cp, so, mw))

def redraw_line(prompt, buffer, max_len, start_row, start_col, curpos):
    echo(f"\r{prompt}{buffer}{' ' * (max_len - len(buffer))}")
    move_cursor(start_row, start_col + len(prompt) + curpos)

def print_matches(matches: list[str]):
    """
    Print matches in neat rows/columns depending on terminal width.
    """
    cols, _ = shutil.get_terminal_size((80, 20))
    longest = max(len(m) for m in matches) + 2
    per_line = max(1, cols // longest)
    for i, m in enumerate(matches, 1):
        echo(m.ljust(longest))
        if i % per_line == 0:
            echo("{f6}")
    if len(matches) % per_line != 0:
        echo("{f6}")

def inputstring(prompt="> ", max_len:int=255, max_width=80, mask:str=None):
    buffer = ""

    curpos = 0
    scroll_offset = 0

    (start_row, start_col) = get_cursor_position()

    prompt_len = len(prompt)
    echo(f"{{curpos:{start_row},{start_col}}}{prompt}", end="", flush=True)

    # Calculate the column where the editable input area begins
    input_col_start = start_col + prompt_len

    _current_display_str = None

    done = False
    while not done:
        # 1. Redraw the input area
        # Calculate the string segment to display
        display_str = buffer[scroll_offset : scroll_offset + max_width]
        if _current_display_str != display_str:
            # Clear the old input (optional, but good practice for clean display)
            # Using ANSI escape codes for cursor positioning and clearing
            echo(f"{{curpos:{start_row},{input_col_start}}}{' ' * max_width}", end="", flush=True)

            # Print the current viewable part of the buffer
            echo(f"{{curpos:{start_row},{input_col_start}}}")
            if mask is not None:
                echo(f"{mask*len(display_str)}", end="", flush=True)
            else:
                echo(f"{display_str}", flush=True, raw=True)

            # Calculate the *display column* for the cursor
            # The cursor display position is: input_col_start + (curpos - scroll_offset)
            cursor_display_col = input_col_start + (curpos - scroll_offset)

            # Position the terminal cursor
            echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)

            _cursor_row = start_row
            _cursor_col = cursor_display_col

            _current_display_str = display_str

##            _current_state.cursor_col = curpos
        
        # 2. get input
        ch = getch(timeout=0.015)
        if ch == "KEY_ENTER":
            return buffer
        elif ch is None:
            continue

        if ch == "KEY_TAB" and callable(completer):
            buffer, curpos, last_matches, tab_count = handle_tab(
                buffer, curpos, completer, last_matches, tab_count,
                prompt, max_len, start_row, start_col
            )

       # 3. Execute Mapped Action (Special Keys)
        if ch in KEY_ACTIONS:
            # The lambda calls the specific helper function, passing all state variables
            # and returns the new state (b, cp, so, mw).
            # We explicitly update the state variables here.
            buffer, curpos, scroll_offset = KEY_ACTIONS[ch](
                buffer, curpos, scroll_offset, max_width
            )
        elif len(ch) == 1:
            if len(buffer) < max_len:
                # Insert the character at the cursor position
                buffer = buffer[:curpos] + ch + buffer[curpos:]
                curpos += 1

        # 4. Handle Scrolling Logic (Key Requirement)
        # Scroll right if cursor moves past the visible right edge
        if curpos >= scroll_offset + max_width:
            # Adjust offset so cursor is at the right edge
            scroll_offset = curpos - max_width + 1

        # Scroll left if cursor moves past the visible left edge
        elif curpos < scroll_offset:
            # Adjust offset so cursor is at the left edge
            scroll_offset = curpos

        # Ensure scroll_offset is never negative
        if scroll_offset < 0:
            scroll_offset = 0

        # Always recalc cursor position
        if mask != "":
            cursor_display_col = input_col_start + (curpos - scroll_offset)
            echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)

        _cursor_row = start_row
        _cursor_col = cursor_display_col

    return buffer
