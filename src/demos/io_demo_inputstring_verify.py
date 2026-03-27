import argparse

from asimov import io
from bbsengine6 import database


def verifyPlayerNameFound(args, name: str, **kwargs) -> bool:
    def _work(conn):
        with database.cursor(conn) as cur:
            sql = "select 1 from empyre.player where moniker=%s"
            dat = (name,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return False
            return True
        return None

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("verifyPlayerNameFound.100: no pool", level="fatal")
            return None
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


def buildargs(args=None, **kwargs: dict):
    parser = argparse.ArgumentParser("io_demo_inputstring_verify")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {
        "databasename": "zoid6",
        "databasehost": "localhost",
        "databaseuser": None,
        "databaseport": 5432,
        "databasepassword": None,
    }
    database.buildargs(parser, defaults, suppress=False)

    return parser


def main():
    parser = buildargs()
    args = parser.parse_args()

    with database.getpool(args) as pool:
        io.inputstring(
            "existing player moniker: ",
            "jam",
            verify=verifyPlayerNameFound,
            args=args,
            pool=pool,
        )


if __name__ == "__main__":
    main()
