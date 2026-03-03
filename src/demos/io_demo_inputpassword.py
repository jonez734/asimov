from asimov.io import inputstring, echo

def main():
    buf = inputstring("password: ")
    echo(f"{{f6:2}}{buf}", end="\n", flush=True)

if __name__ == "__main__":
    main()

