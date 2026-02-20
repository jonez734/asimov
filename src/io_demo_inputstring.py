from asimov.io import echo, screen, inputstring
#from asimov.io.screen import screen as screen_init

if __name__ == "__main__":
    screen.init()
    try:
        buf = inputstring("> ")
        echo(f"{{f6:3}}{buf=}")
    finally:
        echo(f"{{savecursor}}{{decstbm}}{{reset}}{{restorecursor}}", flush=True)
