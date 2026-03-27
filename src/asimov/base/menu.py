from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional
import random
import time

from .io import echo, getch, terminal


def fill(text: str, truncate_len: int, pad_len: int, char: str = " ") -> str:
    return text[:truncate_len].ljust(pad_len, char)


@dataclass
class MenuItem:
    text: str
    value: Any = None
    selectable: bool = True

    def lines(self) -> List[str]:
        """Return lines (multi-line items allowed)."""
        return self.text.splitlines() or [""]


@dataclass
class Menu:
    items: List[MenuItem]
    title: Optional[str] = None
    width: Optional[int] = None
    inner_height: int = 10  # number of lines inside the box
    data_source: Optional[Callable[[], Iterable[MenuItem]]] = None
    current_index: int = 0
    current_page: int = 0
    abs_index: int = 0
    abs_count: int = 0

    pages: List[List[MenuItem]] = None  # computed

    def __post_init__(self):
        if self.width is None:
            self.width = terminal.width()
        if self.data_source:
            self.items = list(self.data_source())
        self.compute_pages()

    def compute_pages(self):
        """Split items into pages without splitting items across pages."""
        self.pages = []
        page = []
        lines_used = 0
        for item in self.items:
            item_height = len(item.lines())
            if lines_used + item_height > self.inner_height:
                if page:
                    self.pages.append(page)
                page = [item]
                lines_used = item_height
            else:
                page.append(item)
                lines_used += item_height
        if page:
            self.pages.append(page)

    @property
    def total_pages(self):
        return len(self.pages) if self.pages else 1

    def visible_items(self) -> List[MenuItem]:
        if not self.pages:
            return []
        return self.pages[self.current_page]

    def truncate(self, text: str, maxlen: int) -> str:
        return text if len(text) <= maxlen else text[: maxlen - 3] + "..."

    @property
    def is_selected(self):
        return self.abs_index == self.current_index

    def draw(self):
        echo("{cls}", end="")
        visible = self.visible_items()
        inner_width = self.width - 4

        ##        echo(f"{inner_width=} {self.width=}")

        # Top border
        echo(f"{{ulcorner}}{{hline:{self.width - 2}}}{{urcorner}}")
        ##        echo(f"asimov.io.menu.draw.100: {_cursor_col=}")
        # Title line
        if self.title:
            title_line = (
                f" {self.title} (Page {self.current_page + 1}/{self.total_pages}) "
            )
            echo(
                f"{{vline}} {fill(title_line, inner_width, inner_width)} {{vline}}",
                wordwrap=False,
            )
            echo(f"{{rtee}}{{hline:{self.width - 2}}}{{ltee}}", wordwrap=False)

        # Draw items
        ##        self.abs_index = 0 # sum(len(p) for p in self.pages[:self.current_page]) # 0
        for item in visible:
            for j, line in enumerate(item.lines()):
                prefix = "  " if j == 0 else "   "
                display_line = f"{prefix}{self.truncate(line, inner_width)}"

                is_selected = self.abs_index == self.current_index
                if is_selected:
                    echo(
                        f"{{vline}} {{inverse}}{fill(display_line, inner_width, inner_width, ' ')}{{reset}} {{vline}}"
                    )
                    # display_line.ljust(inner_width)}{{reset}} {{vline}}", wordwrap=False)
                else:
                    echo(
                        f"{{vline}} {fill(display_line, inner_width, inner_width, ' ')} {{vline}}"
                    )
                    # {display_line.ljust(inner_width,'-')} {{vline}}", wordwrap=False)
            self.abs_index += 1

        # Fill remaining lines
        used_lines = sum(len(item.lines()) for item in visible)
        for _ in range(self.inner_height - used_lines):
            echo(f"{{vline}} {' ' * inner_width} {{vline}}")

        # Bottom border
        echo(f"{{llcorner}}{{hline:{self.width - 2}}}{{lrcorner}}")

    def move_down(self):
        """Move down; if on last item of page go to first item of next page."""
        if self.current_index < len(self.items) - 1:
            self.current_index += 1
            self.abs_count = sum(len(p) for p in self.pages[: self.current_page])
            page_len = len(self.pages[self.current_page])
            if self.current_index >= self.abs_count + page_len:
                self.current_page += 1

    def move_up(self):
        if self.current_index > 0:
            self.current_index -= 1
            # move to previous page if current_index is before visible page
            self.abs_count = sum(len(p) for p in self.pages[: self.current_page])
            if self.current_index < self.abs_count:
                self.current_page -= 1
                return True
        return False

    def adjust_page_for_current(self):
        """Ensure current_index is visible on current page."""
        self.abs_count = 0
        for i, page in enumerate(self.pages):
            page_len = len(page)
            if self.abs_count <= self.current_index < self.abs_count + page_len:
                self.current_page = i
                return
            self.abs_count += page_len

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.current_index = sum(len(p) for p in self.pages[: self.current_page])

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.current_index = sum(len(p) for p in self.pages[: self.current_page])

    def refresh_from_db(self):
        if self.data_source:
            self.items = list(self.data_source())
            self.compute_pages()
            self.current_index = 0
            self.current_page = 0

    def run(self) -> Optional[MenuItem]:
        _changed = True
        while True:
            if _changed is True:
                self.draw()

            ch = getch(timeout=1)
            if ch is None:
                continue
            elif ch in ("q", "Q", "KEY_ESC"):
                return None
            elif ch in ("KEY_ENTER"):
                return self.items[self.current_index]
            elif ch in ("j", "J", "KEY_DOWN"):
                self.move_down()
            elif ch in ("k", "K", "KEY_UP"):
                self.move_up()
            elif ch in (">", "]", "KEY_PAGEDOWN"):
                self.next_page()
            elif ch in ("<", "[", "KEY_PAGEUP"):
                self.prev_page()
            elif ch == "r":
                self.refresh_from_db()
            else:
                _changed = False


#            if _changed:
#                self.adjust_page_for_current()


def menu(items=None, title=None, query=None, **kwargs):
    if items is None:
        items = []
    menu_items = [MenuItem(text=i) if not isinstance(i, MenuItem) else i for i in items]
    m = Menu(menu_items, title=title, data_source=query, **kwargs)
    return m.run()


def generate_random_items(n=20):
    base = [
        "Alfa",
        "Bravo",
        "Charlie",
        "Delta",
        "Echo",
        "Foxtrot",
        "Golf",
        "Hotel",
        "India",
        "Juliet",
        "Kilo",
        "Lima",
        "Mike",
        "November",
        "Oscar",
        "Papa",
        "Quebec",
        "Romeo",
        "Sierra",
        "Tango",
        "Uniform",
        "Victor",
        "Whiskey",
        "X-ray",
        "Yankee",
        "Zulu",
    ]
    items = []
    for _ in range(n):
        word = random.choice(base)
        if random.random() < 0.3:
            text = f"{word}\nSecond line of {word}\n{word} Third line"
        else:
            text = word
        items.append(MenuItem(text))
    return items


if __name__ == "__main__":
    random.seed(time.time())
    demo_items = generate_random_items(25)
    selected = menu(
        items=demo_items, title="Random Menu Demo", inner_height=10, width=100
    )
    echo("{reset}")
    if selected:
        echo(f"You selected: {selected.text}")
    else:
        echo("Menu canceled.")
