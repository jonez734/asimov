from asimov.io import echo
from asimov.util import screen_init
from asimov.inputstring import inputstring

if __name__ == "__main__":
    screen_init()
    try:
        buf = inputstring("> ")
        echo(f"{{f6:3}}{buf=}")
    finally:
        echo(f"{{savecursor}}{{decstbm}}{{reset}}{{restorecursor}}", flush=True)
