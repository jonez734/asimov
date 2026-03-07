import argparse

from bbsengine6 import io

from . import lib as libasimov
from . import conf
from .util import capture_device_type

def buildargs(args=None, **kwargs:dict):
    parser = argparse.ArgumentParser("asimov")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    parser.add_argument("--basedir", default="$HOME/projects/playingcarddata")
    parser.add_argument("--set-name", default="bicycle")
    parser.add_argument("--main", type=str, default="dashboard")
    parser.add_argument("--capture-device", type=capture_device_type, default=conf.CAPTURE_DEVICE)
    parser.add_argument("--capture-width", type=int, default=conf.CAPTURE_WIDTH)
    parser.add_argument("--capture-height", type=int, default=conf.CAPTURE_HEIGHT)
    parser.add_argument("--capture-fps", type=int, default=conf.CAPTURE_FPS)

#    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
#    database.buildargs(parser, defaults)

    return parser

if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

    try:
        libasimov.runmodule(args, f"main_{args.main}")
    except KeyboardInterrupt:
        io.echo("{/all}*INTR*")
    except EOFError:
        io.echo("{/all}*EOF*")
    finally:
        io.echo(f"{{decsc}}{{curpos:{io.terminal.height()},0}}{{el}}{{reset}}{{decrc}}")
