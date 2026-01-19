import argparse

from asimov import io
from bbsengine6 import database

def verifyPlayerNameFound(name:str, *, args) -> bool:
    if hasattr(args, "pool") is True:
        pool = args.pool
    else:
        pool = database.getpool(args)
        if pool is None:
            io.echo(f"database.getpool() failed", level="error")
            return None

    with pool:
        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                sql = "select 1 from empyre.player where moniker=%s"
                dat = (name,)
                cur.execute(sql, dat)
                if cur.rowcount == 0:
                    io.echo("false")
                    return False
                io.echo("true")
                return True

def buildargs(args=None, **kwargs:dict):
    parser = argparse.ArgumentParser("io_demo_inputstring_verify")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    database.buildargs(parser, defaults, suppress=False)

    return parser

def main():
    parser = buildargs()
    args = parser.parse_args()

    args.pool = database.getpool(args)
    if args.pool is None:
        io.echo("pool problem", flush=True)
        return
    io.echo(f"{args=}", level="critical", flush=True)
    io.inputstring("prompt here: ", "jam", verify=verifyPlayerNameFound, args=args)

if __name__ == "__main__":
    main()
