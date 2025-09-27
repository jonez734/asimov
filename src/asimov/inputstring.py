from asimov.getch import getch_nonblocking as getch
from asimov.io import echo, get_cursor_position
from bbsengine6 import screen

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
    return buffer, curpos, scroll_offset

# --- New Helper Function for ^Y ---
def handle_yank(buffer, curpos, scroll_offset, max_width):
    global YANK_BUFFER
    yank_text = YANK_BUFFER

    # 1. Insert the yanked text at the cursor position
    buffer = buffer[:curpos] + yank_text + buffer[curpos:]

    # 2. Move the cursor past the inserted text
    curpos += len(yank_text)

    # Scroll offset adjustment will be handled by the main loop's scrolling logic
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

def inputstring(prompt="> ", max_len:int=255, max_width=80):
    buffer = ""

    curpos = 0
    scroll_offset = 0

    (start_row, start_col) = get_cursor_position()

    prompt_len = len(prompt)
    echo(f"{{curpos:{start_row},{start_col}}}{prompt}", end="", flush=True)

    # Calculate the column where the editable input area begins
    input_col_start = start_col + prompt_len

    done = False
    while not done:
        # 1. Redraw the input area
        # Calculate the string segment to display
        display_str = buffer[scroll_offset : scroll_offset + max_width]
#        echo(f"{display_str=} {scroll_offset=} {max_width=}", flush=True)
        
        # Clear the old input (optional, but good practice for clean display)
        # Using ANSI escape codes for cursor positioning and clearing
        echo(f"{{curpos:{start_row},{input_col_start}}}{' ' * max_width}", end="", flush=True)

        # Print the current viewable part of the buffer
        echo(f"{{curpos:{start_row},{input_col_start}}}{display_str}", end="", flush=True)

        # Calculate the *display column* for the cursor
        # The cursor display position is: input_col_start + (curpos - scroll_offset)
        cursor_display_col = input_col_start + (curpos - scroll_offset)
        
        # Position the terminal cursor
        echo(f"{{curpos:{start_row},{cursor_display_col}}}", end="", flush=True)
        
        # 2. get input
        ch = getch(timeout=0.015)
        screen.setbottombar("asimov.inputstring", f"{ch=}")
        echo(f"{ch=}", flush=True)
        if ch == "KEY_ENTER":
            return buffer
        elif ch is None:
            continue

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

        # 5. Handle Scrolling Logic (Key Requirement)
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

    # --- Final Cleanup ---
#    echo(f"{{f6}}", end="", flush=True)
    return buffer

if __name__ == "__main__":
    screen.init()
    try:
        buf = inputstring("> ")
        echo(f"{{f6:3}}{buf=}")
    finally:
        echo(f"{{savecursor}}{{decstbm}}{{reset}}{{restorecursor}}aaa", flush=True)
