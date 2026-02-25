import time
import random
import argparse

from asimov.io import echo
from asimov.listbox import ListboxItem, Listbox
from asimov import listbox

def generate_random_items(n=20):
    base = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel",
            "India", "Juliet", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa",
            "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey",
            "X-ray", "Yankee", "Zulu"]

    items = []
    for _ in range(n):
        word = random.choice(base)
        if random.random() < 0.3:
            text = f"{word}\nSecond line of {word}\n{word} Third line"
        else:
            text = word
        items.append(ListboxItem(text))
    return items


if __name__ == "__main__":
    args = argparse.Namespace()

    random.seed(time.time())
    demo_items = generate_random_items(25)
    l = Listbox(args, items=demo_items, title="Random Listbox Demo", inner_height=10)
    selected = l.run()
    echo("{reset}")
    if selected is None:
        echo("Menu canceled")
    elif selected is False:
        echo("error")
    else:
        echo(f"You selected: {str(selected)}")
