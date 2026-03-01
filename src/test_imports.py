#!/usr/bin/env python3
"""Test all asimov subpackage imports."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_subpackages():
    tests = [
        ("base", lambda: __import__("asimov", fromlist=["base"]).base),
        ("io", lambda: __import__("asimov", fromlist=["io"]).io),
        ("net", lambda: __import__("asimov", fromlist=["net"]).net),
        ("modules", lambda: __import__("asimov", fromlist=["modules"]).modules),
        ("common", lambda: __import__("asimov", fromlist=["common"]).common),
        (
            "playingcard",
            lambda: __import__("asimov", fromlist=["playingcard"]).playingcard,
        ),
    ]

    print("=" * 60)
    print("ASIMOV SUBPACKAGE IMPORT TESTS")
    print("=" * 60)

    all_passed = True
    for name, import_fn in tests:
        try:
            module = import_fn()
            print(f"{name:15} OK       - {module}")
        except Exception as e:
            print(f"{name:15} FAIL     - {e}")
            all_passed = False

    print("=" * 60)
    return all_passed


def test_common_exports():
    print("\nTesting common exports:")
    from asimov import common

    exports = ["ThreadSafeContext", "OneEuroFilter", "safe_path", "get_safe_path"]
    for exp in exports:
        try:
            getattr(common, exp)
            print(f"  {exp:20} OK")
        except AttributeError as e:
            print(f"  {exp:20} FAIL - {e}")


def test_io_exports():
    print("\nTesting io exports:")
    from asimov import io

    exports = ["echo", "echo_traceback", "rendered_length", "get_cursor_position"]
    for exp in exports:
        try:
            getattr(io, exp)
            print(f"  {exp:20} OK")
        except AttributeError as e:
            print(f"  {exp:20} FAIL - {e}")


def test_playingcard_exports():
    print("\nTesting playingcard exports:")
    from asimov.playingcard import cards, detect, load_set, templates

    exports = [
        ("cards", cards),
        ("detect", detect),
        ("load_set", load_set),
        ("templates", templates),
    ]
    for name, exp in exports:
        try:
            exp
            print(f"  {name:20} OK")
        except Exception as e:
            print(f"  {name:20} FAIL - {e}")


if __name__ == "__main__":
    success = test_subpackages()
    test_common_exports()
    test_io_exports()
    test_playingcard_exports()
    print()
    sys.exit(0 if success else 1)
