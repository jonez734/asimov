from asimov.getch import getch_nonblocking as getch
from asimov.io import echo, get_cursor_position

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
        
        ch = getch()
        if ch == "KEY_ENTER":
            return buffer
        elif ch is None:
            continue
        elif ch == "KEY_HOME":
            curpos = 0
        elif ch == "KEY_END":
            curpos = len(buffer)
        elif ch == "KEY_LEFT":
            if curpos > 0:
                curpos -= 1
            else:
                echo(f"{{bell}}", flush=True)
        elif ch == "KEY_RIGHT":
            if curpos < len(buf):
                curpos += 1
            else:
                echo(f"{{bell}}", flush=True)

        elif ch == "KEY_BACKSPACE":
            if curpos > 0:
                # Delete character before the cursor
                buffer = buffer[:curpos-1] + buffer[curpos:]
                curpos -= 1
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
    buf = inputstring("> ")
    echo(f"{{f6:3}}{buf=}{{f6:3}}")
