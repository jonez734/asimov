from asimov.io import echo
from asimov.menu import MenuItem, Menu

# Demo items: some are multi-line
demo_items = [
    MenuItem("Alpha"),
    MenuItem("Bravo\nSecond line of Bravo"),
    MenuItem("Charlie"),
    MenuItem("Delta\nSecond line of Delta"),
    MenuItem("Echo"),
    MenuItem("Foxtrot\nSecond line of Foxtrot"),
    MenuItem("Golf"),
    MenuItem("Hotel\nSecond line of Hotel"),
    MenuItem("India"),
    MenuItem("Juliet\nSecond line of Juliet"),
]

# Run menu
if demo_items is None:
        items = []
    menu_items = [MenuItem(text=i) if not isinstance(i, MenuItem) else i for i in items]
    m = Menu(menu_items, title=title, data_source=query, **kwargs)
    return m.run()

selected = Menu(items=demo_items, title="Demo Menu", inner_height=8)  # inner_height smaller to test pages

if selected:
    echo(f"You selected: {selected.text}")
else:
    echo("Menu canceled.")
