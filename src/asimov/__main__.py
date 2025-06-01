import argparse
import time, locale

from bbsengine6 import io, module, screen

#from . import lib

import asimov.main

def buildargs(args=None, **kw:dict):
    parser = argparse.ArgumentParser("asimov")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

#    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
#    database.buildargs(parser, defaults)

    return parser

if __name__ == "__main__":
    parser = buildargs()
    args = parser.parse_args()

#    pool = database.getpool(args)
#    session.start(args, pool=pool)

    screen.init()

    locale.setlocale(locale.LC_ALL, "")
    time.tzset()

    try:
        asimov.main.main(args) # module.run(args, "main") # main(args) # lib.runsubmodule(args, "main") # module.main(args)
    except KeyboardInterrupt:
        io.echo("{/all}*INTR*")
    except EOFError:
        io.echo("{/all}*EOF*")
    finally:
        io.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (io.getterminalheight()))
