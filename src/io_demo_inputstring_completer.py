#!/usr/bin/env python3
"""
Demo: inputstring() with Completer class and function.

Tests tab completion using:
1. A callable class (subclass of Completer)
2. A normal function passed to Completer constructor
3. **kwargs for database parameters

Run: python io_demo_inputstring_completer.py
"""
import sys
sys.path.insert(0, 'src')

from asimov.io import echo, screen, inputstring
from asimov.io.inputstring import Completer

# Mock database of player names
PLAYERS = [
    "alice", "bob", "charlie", "chris",
    "dave", "diana", "eve", "frank",
    "grace", "henry", "iris", "jack",
    "karen", "leo", "mary", "nancy"
]

def main():
    screen.init()
    echo("{yellow}=== Demo: inputstring with Completer ===")
    
    try:
        # Demo 1: Callable class with override
        echo("{cyan}Demo 1: Subclass Completer with get_matches() override{f6}Type a name starting with 'a', 'b', 'c', etc. Press TAB for completions.")
        
        class PlayerCompleter(Completer):
            """Completer that returns player names from 'database'."""
            
            def get_matches(self, prefix, **kwargs):
                """Return player names matching prefix.
                
                Args:
                    prefix: The text prefix to match
                    **kwargs: Additional args (conn, pool, etc.)
                """
                if not prefix:
                    return PLAYERS  # Return all when empty
                prefix_lower = prefix.lower()
                matches = [p for p in PLAYERS if p.startswith(prefix_lower)]
                return matches
        
        name1 = inputstring("Select player: ", completer=PlayerCompleter())
        echo(f"{{f6}}Selected: {name1}")
        
        # Demo 2: Function passed to constructor with kwargs
        echo("{cyan}Demo 2: Pass function to Completer with kwargs{f6}Type a color (red, green, blue, etc.) Press TAB.")
        
        COLORS = ["red", "green", "blue", "yellow", "cyan", "magenta", "orange", "purple"]
        
        def color_completer(prefix, conn=None):
            """Return colors matching prefix."""
            if not prefix:
                return COLORS  # Return all when empty
            prefix_lower = prefix.lower()
            return [c for c in COLORS if c.startswith(prefix_lower)]
        
        name2 = inputstring(
            "Select color: ", 
            completer=Completer(color_completer, conn="db_connection")
        )
        echo(f"{{f6}}Selected: {name2}")
        
        # Demo 3: Lambda function
        echo("{cyan}Demo 3: Lambda function passed directly{f6}Type a fruit (apple, banana, cherry) Press TAB.")
        
        FRUITS = ["apple", "banana", "cherry", "date", "elderberry"]
        
        fruit = inputstring(
            "Select fruit: ",
            completer=Completer(lambda p, **kwargs: [f for f in FRUITS if f.startswith(p.lower())])
        )
        echo(f"{{f6}}Selected: {fruit}")
        
        # Demo 4: Using direct kwargs for completer
        echo("{cyan}Demo 4: Using direct kwargs for completer{f6}Type a vegetable (carrot, potato, etc.)")
        
        VEGGIES = ["carrot", "potato", "tomato", "cucumber", "celery"]
        
        def veggie_completer(prefix, category=None):
            if not prefix:
                return VEGGIES
            return [v for v in VEGGIES if v.startswith(prefix.lower())]
        
        veg = inputstring(
            "Select veggie: ",
            completer=Completer(veggie_completer),
            category="root_vegetables"
        )
        echo(f"{{f6}}Selected: {veg}")
        
        echo("{green}All demos completed!")
        
    finally:
        echo("{savecursor}{decstbm}{reset}{restorecursor}", flush=True)


if __name__ == "__main__":
    main()
