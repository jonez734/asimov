"""
Terminal menu system with multi-line items, pagination, and keyboard navigation.

This file contains both the menu system implementation and a demo script.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Any
import time

from asimov.io.echo import echo
from asimov.io.getch import getch_str as getch
from asimov.io import terminal


def fill(text: str, truncate_len: int, pad_len: int, char: str = " ") -> str:
    return text[:truncate_len].ljust(pad_len, char)


@dataclass
class KeyHandler:
    """Represents a key handler with callable, help text, and disabled state."""

    func: Callable
    help: str | Callable
    disabled: bool = False


class MenuItem:
    """A menu item that can span multiple lines."""

    def __init__(
        self,
        content: str,
        disabled: bool = False,
        displayed: bool = True,
        keyhandlers: Optional[dict[str, KeyHandler]] = None,
        data: Any = None,
    ):
        self.content = content
        self.disabled = disabled
        self.displayed = displayed
        self.is_current = False
        self.keyhandlers = keyhandlers or {}
        self.data = data
        self._lines = content.split("\n")

    @property
    def height(self) -> int:
        """Number of lines this item occupies. Override in subclasses if needed."""
        return 1

    def draw(self, inner_width: int) -> list[str]:
        """Draw this menu item and return list of lines."""
        lines = []
        # Only show up to self.height lines
        display_lines = self._lines[: self.height]

        for i, line in enumerate(display_lines):
            # First line gets 2-space prefix, subsequent lines get 3-space prefix
            prefix = "  " if i == 0 else "   "
            content = fill(line, inner_width - len(prefix), inner_width - len(prefix))

            if self.is_current:
                full_line = f"{{vline}} {{inverse}}{prefix}{content} {{reset}}{{vline}}"
            else:
                full_line = f"{{vline}} {prefix}{content} {{vline}}"

            lines.append(full_line)

        return lines

    def handle_key(self, key: str) -> bool:
        """Handle a key press. Returns the result of calling the handler, or False if not handled."""
        if key in self.keyhandlers:
            handler = self.keyhandlers[key]
            if not handler.disabled and callable(handler.func):
                return handler.func()
        return False


class Menu:
    """Terminal menu with pagination and keyboard navigation."""

    def __init__(
        self,
        title: str,
        items: Optional[list[MenuItem]] = None,
        width: Optional[int] = None,
        lines_per_page: int = 10,
        keyhandlers: Optional[dict[str, KeyHandler]] = None,
    ):
        self._title = title
        self._all_items = items or []  # Only used for default implementation
        self._width = width
        self.lines_per_page = lines_per_page
        self.keyhandlers = keyhandlers or self._default_keyhandlers()

        self.current_page = 0
        self.current_item_index = 0  # Index within current page (0 to itemsperpage-1)
        self.total_displayed_items = len(
            [item for item in self._all_items if item.displayed]
        )
        self.last_key = None
        self.last_key_time = 0

        # Track what needs redrawing
        self._previous_current_index = None
        self._item_row_positions = {}  # Maps page index to row offset from menu start
        self._current_page_items = []  # Cache of current page

    @property
    def width(self) -> int:
        """Menu width, defaults to terminal width if not specified."""
        if self._width is None:
            return terminal.width()
        return self._width

    @property
    def inner_width(self) -> int:
        """Width inside the box borders (excludes left/right borders and padding)."""
        return self.width - 4  # 2 for borders, 2 for padding

    @property
    def inner_height(self) -> int:
        """Height available for menu items."""
        return self.lines_per_page

    @property
    def total_height(self) -> int:
        """Total height of the menu including borders."""
        # Top border (1) + title (1) + separator (1) + items area + bottom border (1) + prompt (1)
        return 3 + self.inner_height + 1 + 1

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        if self.total_displayed_items == 0:
            return 1
        # Calculate pages based on fitting items into available lines
        pages = 1
        current_lines = 0
        for item in [item for item in self._all_items if item.displayed]:
            if current_lines + item.height > self.lines_per_page:
                pages += 1
                current_lines = item.height
            else:
                current_lines += item.height
        return pages

    @property
    def title(self) -> str:
        """Title with page info appended."""
        t = f"{self._title} (Page {self.current_page + 1}/{self.total_pages})"
        return fill(t, self.inner_width, self.inner_width)

    def add_item(self, item: MenuItem):
        """Add a menu item (only for default in-memory implementation)."""
        self._all_items.append(item)
        self.total_displayed_items = len(
            [item for item in self._all_items if item.displayed]
        )

    def clear_items(self):
        """Clear all menu items (only for default in-memory implementation)."""
        self._all_items.clear()
        self.total_displayed_items = 0
        self.current_page = 0
        self.current_item_index = 0
        self._previous_current_index = None
        self._item_row_positions.clear()
        self._current_page_items = []

    def _default_keyhandlers(self) -> dict[str, KeyHandler]:
        """Default key handlers for the menu."""
        return {
            "KEY_ENTER": KeyHandler(self._handle_key_enter, "select the current item"),
            "KEY_UP": KeyHandler(self._handle_key_up, "move up"),
            "KEY_DOWN": KeyHandler(self._handle_key_down, "move down"),
            "KEY_HOME": KeyHandler(self._handle_key_home, "go to first item"),
            "KEY_END": KeyHandler(self._handle_key_end, "go to last item"),
            "KEY_ESC": KeyHandler(self._handle_key_esc, "exit menu"),
        }

    def _is_double_press(self, key: str, timeout: float = 1.0) -> bool:
        """Check if key was pressed twice within timeout."""
        current_time = time.time()
        is_double = self.last_key == key and current_time - self.last_key_time < timeout
        self.last_key = key
        self.last_key_time = current_time
        return is_double

    def _handle_key_enter(self):
        """Return the current menu item."""
        if self._current_page_items and 0 <= self.current_item_index < len(
            self._current_page_items
        ):
            item = self._current_page_items[self.current_item_index]
            if not item.disabled:
                return item
        return False

    def _handle_key_up(self):
        """Move up one item."""
        if self.total_displayed_items == 0:
            return False

        # Single column: simple up movement
        if self.current_item_index > 0:
            self.current_item_index -= 1
        else:
            # Move to previous page
            if self.current_page > 0:
                self.current_page -= 1
                self._current_page_items = self.fetchpage()
                self.current_item_index = len(self._current_page_items) - 1
                self.draw(complete=True)
            else:
                # Wrap to last page
                self.current_page = self.total_pages - 1
                self._current_page_items = self.fetchpage()
                self.current_item_index = len(self._current_page_items) - 1
                self.draw(complete=True)
            return True

        self.draw(complete=False)
        return True

    def _handle_key_down(self):
        """Move down one item."""
        if self.total_displayed_items == 0:
            return False

        # Single column: simple down movement
        if self.current_item_index < len(self._current_page_items) - 1:
            self.current_item_index += 1
        else:
            # Move to next page
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self._current_page_items = self.fetchpage()
                self.current_item_index = 0
                self.draw(complete=True)
            else:
                # Wrap to first page
                self.current_page = 0
                self._current_page_items = self.fetchpage()
                self.current_item_index = 0
                self.draw(complete=True)
            return True

        self.draw(complete=False)
        return True

    def _handle_key_home(self):
        """Go to first item of page, or first item of first page if pressed twice."""
        if self._is_double_press("KEY_HOME"):
            self.current_page = 0
            self._current_page_items = self.fetchpage()
            self.current_item_index = 0
            self.draw(complete=True)
        else:
            self.current_item_index = 0
            self.draw(complete=False)
        return True

    def _handle_key_end(self):
        """Go to last item of page, or last item of last page if pressed twice."""
        if self.total_displayed_items == 0:
            return False

        if self._is_double_press("KEY_END"):
            self.current_page = self.total_pages - 1
            self._current_page_items = self.fetchpage()
            self.current_item_index = len(self._current_page_items) - 1
            self.draw(complete=True)
        else:
            self.current_item_index = len(self._current_page_items) - 1
            self.draw(complete=False)
        return True

    def _handle_key_esc(self):
        """Exit the menu."""
        return None

    def fetchpage(self) -> list[MenuItem]:
        """
        Fetch the current page of menu items.

        Override this method for database-backed menus. The default implementation
        uses in-memory items. When overriding:
        - Return a list of MenuItems for the current page
        - Use self.current_page and self.lines_per_page to determine which items to fetch
        - Set self.total_displayed_items to the total number of items available
        - Filter out items with displayed=False if needed
        """
        if not self._all_items:
            return []

        # Filter for displayed items and update total_displayed_items count
        displayed = [item for item in self._all_items if item.displayed]
        self.total_displayed_items = len(displayed)

        # Find items that fit on the current page based on line height
        page_items = []
        current_lines = 0
        pages_seen = 0

        for item in displayed:
            # Check if adding this item would exceed page capacity
            if current_lines + item.height > self.lines_per_page:
                # Start new page
                pages_seen += 1
                current_lines = 0

            # If we're on the target page, add this item
            if pages_seen == self.current_page:
                if current_lines + item.height <= self.lines_per_page:
                    page_items.append(item)
                    current_lines += item.height
                else:
                    # This page is full
                    break

            # Track lines for page calculation
            if pages_seen < self.current_page:
                current_lines += item.height

        return page_items

    def draw(self, complete: bool = False):
        """Draw the menu."""
        # Fetch current page if needed
        if complete or not self._current_page_items:
            self._current_page_items = self.fetchpage()

        if complete:
            # Position cursor at top of menu from saved prompt position
            echo("{decrc}", end="")  # Restore to prompt position
            # Move up: 3 (header) + lines_per_page (items) + 1 (bottom border)
            menu_height = 3 + self.lines_per_page + 1
            echo(f"{{cursorup:{menu_height}}}", end="")

            # Draw top border with title
            echo(f"{{ulcorner}}{{hline:{self.width - 2}}}{{urcorner}}")
            echo(f"{{vline}} {self.title} {{vline}}")
            echo(f"{{ltee}}{{hline:{self.width - 2}}}{{rtee}}")

        current_row = 0
        self._item_row_positions.clear()

        if complete:
            # Draw all items
            for i, item in enumerate(self._current_page_items):
                item.is_current = i == self.current_item_index

                self._item_row_positions[i] = current_row
                item_lines = item.draw(self.inner_width)
                for line in item_lines:
                    echo(line)
                    current_row += 1

            # Fill remaining space with blank lines
            while current_row < self.inner_height:
                echo(f"{{vline}}{' ' * (self.width - 2)}{{vline}}")
                current_row += 1

            # Draw bottom border
            echo(f"{{llcorner}}{{hline:{self.width - 2}}}{{lrcorner}}")

            # Cursor is now back at prompt line naturally

            # Update tracking
            self._previous_current_index = self.current_item_index
        else:
            # Incremental update: only redraw changed items
            items_to_redraw = set()

            if (
                self._previous_current_index is not None
                and self._previous_current_index != self.current_item_index
            ):
                items_to_redraw.add(self._previous_current_index)
                items_to_redraw.add(self.current_item_index)

                # Clear is_current on previous item
                if 0 <= self._previous_current_index < len(self._current_page_items):
                    self._current_page_items[
                        self._previous_current_index
                    ].is_current = False

            # Calculate row positions - simplified for constant height items
            for i, item in enumerate(self._current_page_items):
                self._item_row_positions[i] = i * item.height

            # Redraw only changed items using relative positioning from prompt
            for item_idx in items_to_redraw:
                if item_idx not in self._item_row_positions:
                    continue

                if 0 <= item_idx < len(self._current_page_items):
                    item = self._current_page_items[item_idx]
                    item.is_current = item_idx == self.current_item_index

                    # Simplified positioning for constant height items
                    row_offset = self._item_row_positions[item_idx]

                    # Total lines used by all items (all same height)
                    total_item_lines = len(self._current_page_items) * item.height

                    # Blank lines that were filled
                    blank_lines = self.lines_per_page - total_item_lines

                    # Distance from prompt: 1 (bottom border) + blank_lines + distance from bottom of items
                    lines_from_bottom_of_items = total_item_lines - row_offset

                    # Redraw the item line by line
                    item_lines = item.draw(self.inner_width)
                    for line_num, line in enumerate(item_lines):
                        # Calculate up amount: bottom border + blanks + items below us + lines within our item
                        up_amount = (
                            1 + blank_lines + lines_from_bottom_of_items - line_num
                        )
                        echo(f"{{decrc}}{{cha}}{{cursorup:{up_amount}}}{line}", end="")

            # Restore cursor to prompt position
            echo("{decrc}", end="")

            # Update tracking
            self._previous_current_index = self.current_item_index

    def run(self, prompt: str = "menu: ") -> Optional[MenuItem]:
        """Run the menu loop and return selected item or None."""
        # Initial draw
        self.draw(complete=True)
        echo(
            f"{prompt}{{decsc}}", end="", flush=True
        )  # Display prompt and save cursor position

        while True:
            key = getch()

            if key is None:
                # Timeout - don't redisplay prompt
                continue

            # Try current item's keyhandler first
            result = False

            if self._current_page_items and 0 <= self.current_item_index < len(
                self._current_page_items
            ):
                result = self._current_page_items[self.current_item_index].handle_key(
                    key
                )

                if result is None:
                    return None  # Exit menu
                elif isinstance(result, MenuItem):
                    return result  # Item selected
                elif result is True:
                    self.draw(complete=False)
                    continue  # Key was handled, redraw and get next key
                # else: result is False, fall through to Menu's keyhandler

            # Try menu's keyhandler if item didn't handle it
            if key in self.keyhandlers and not self.keyhandlers[key].disabled:
                handler = self.keyhandlers[key]
                if callable(handler.func):
                    result = handler.func()

                    # Handle special return values
                    if result is None:  # Handler wants to exit (e.g., ESC)
                        return None
                    elif isinstance(result, MenuItem):  # ENTER pressed
                        return result
                    # Handler already called draw() if needed


# =============================================================================
# DEMO SCRIPT
# =============================================================================


def demo():
    """Demo script for the menu system."""
    # Create some test menu items
    items = [
        MenuItem("Simple item 1"),
        MenuItem("Simple item 2"),
        MenuItem("Multi-line item:\nThis is line 2\nAnd this is line 3"),
        MenuItem("Disabled item", disabled=False),  # Changed to False so we can test it
        MenuItem("Another simple item"),
        MenuItem("Item with data", data={"id": 123, "name": "test"}),
        MenuItem(
            "Long item that will get truncated if it exceeds the width of the menu box"
        ),
        MenuItem("Item 7"),
        MenuItem("Item 8"),
        MenuItem("Item 9"),
        MenuItem("Item 10"),
        MenuItem("Item 11 - page 2"),
        MenuItem("Item 12"),
        MenuItem("Last item"),
    ]

    # Create menu
    menu = Menu(title="Test Menu", items=items, width=60, lines_per_page=10)

    # Add another item dynamically
    menu.add_item(MenuItem("Dynamically added item"))

    print("Menu Demo - Controls:")
    print("  UP/DOWN: Navigate")
    print("  HOME/END: Jump to first/last (press twice for first/last page)")
    print("  ENTER: Select item")
    print("  ESC: Exit")
    print("\nStarting menu...\n")

    # Run the menu
    selected = menu.run(prompt="Select an option: ")

    if selected:
        print(f"\n\nYou selected: {selected.content}")
        if selected.data:
            print(f"Item data: {selected.data}")
    else:
        print("\n\nMenu cancelled.")


if __name__ == "__main__":
    demo()
