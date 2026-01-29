from asimov import io

def main(args=None, **kwargs):
    res = io.inputstring("noneok test: ", noneok=False)
    io.echo(res)

if __name__ == "__main__":
    main()
