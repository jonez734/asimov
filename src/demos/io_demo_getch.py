from asimov.io.getch import getch_str as getch
from asimov.io.echo import echo


def main():
    #    screen_init()

    #    setbottombar("foo", "bar")

    echo("prompt here: {decsc}", end="")
    done = False
    while not done:
        ch = getch()
        #        setbottombar("getch demo", f"{ch=}")
        if ch == "KEY_ENTER":
            done = True
        echo(f"{ch}{{f6}}", end="", flush=True)


if __name__ == "__main__":
    main()
