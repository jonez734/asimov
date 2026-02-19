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
    echo("{yellow}=== Demo: inputstring with Completer ==={f6}")
    echo("{f6}")
    
    try:
        # Demo 1: Callable class with override
        echo("{cyan}Demo 1: Subclass Completer with get_matches() override{f6}")
        echo("Type a name starting with 'a', 'b', 'c', etc. Press TAB for completions.{f6}")
        
        class PlayerCompleter(Completer):
            """Completer that returns player names from 'database'."""
            
            def get_matches(self, prefix, conn=None, pool=None):
                """Return player names matching prefix.
                
                Args:
                    prefix: The text prefix to match
                    conn: Database connection (example kwarg)
                    pool: Connection pool (example kwarg)
                """
                if not prefix:
                    return []
                prefix_lower = prefix.lower()
                matches = [p for p in PLAYERS if p.startswith(prefix_lower)]
                return matches
        
        name1 = inputstring("Select player: ", completer=PlayerCompleter())
        echo(f"{{f6}}Selected: {name1}{{f6}}")
        echo("{f6}")
        
        # Demo 2: Function passed to constructor with kwargs
        echo("{cyan}Demo 2: Pass function to Completer with kwargs{f6}")
        echo("Type a color (red, green, blue, etc.) Press TAB.{f6}")
        
        COLORS = ["red", "green", "blue", "yellow", "cyan", "magenta", "orange", "purple"]
        
        def color_completer(prefix, conn=None):
            """Return colors matching prefix."""
            if not prefix:
                return []
            prefix_lower = prefix.lower()
            return [c for c in COLORS if c.startswith(prefix_lower)]
        
        name2 = inputstring(
            "Select color: ", 
            completer=Completer(color_completer, conn="db_connection")
        )
        echo(f"{{f6}}Selected: {name2}{{f6}}")
        echo("{f6}")
        
        # Demo 3: Lambda function
        echo("{cyan}Demo 3: Lambda function passed directly{f6}")
        echo("Type a fruit (apple, banana, cherry) Press TAB.{f6}")
        
        FRUITS = ["apple", "banana", "cherry", "date", "elderberry"]
        
        fruit = inputstring(
            "Select fruit: ",
            completer=Completer(lambda p, **kwargs: [f for f in FRUITS if f.startswith(p.lower())] if p else [])
        )
        echo(f"{{f6}}Selected: {fruit}{{f6}}")
        echo("{f6}")
        
        # Demo 4: Using completer_kwargs parameter
        echo("{cyan}Demo 4: Using completer_kwargs parameter{f6}")
        echo("Type a vegetable (carrot, potato, etc.) Press TAB.{f6}")
        
        VEGGIES = ["carrot", "potato", "tomato", "cucumber", "celery"]
        
        def veggie_completer(prefix, category=None):
            if not prefix:
                return []
            return [v for v in VEGGIES if v.startswith(prefix.lower())]
        
        veg = inputstring(
            "Select veggie: ",
            completer=Completer(veggie_completer),
            completer_kwargs={"category": "root_vegetables"}
        )
        echo(f"{{f6}}Selected: {veg}{{f6}}")
        echo("{f6}")
        
        echo("{green}All demos completed!{f6}")
        
    finally:
        echo("{savecursor}{decstbm}{reset}{restorecursor}", flush=True)


if __name__ == "__main__":
    main()
