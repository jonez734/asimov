#!/usr/bin/env python3
"""Tests for float_playingcard module."""

import sys
import os

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import float_playingcard
    assert float_playingcard.init(None) is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import float_playingcard
    assert float_playingcard.main(None) is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import float_playingcard
    assert float_playingcard.access(None, "run") is True
    print("  test_access_returns_true -> PASS")


def test_get_stateful_keys():
    """Test get_stateful_keys returns CARD."""
    from asimov.modules import float_playingcard
    assert float_playingcard.get_stateful_keys() == ["CARD"]
    print("  test_get_stateful_keys -> PASS")


def test_buildargs_returns_none():
    """Test buildargs returns None."""
    from asimov.modules import float_playingcard
    assert float_playingcard.buildargs(None) is None
    print("  test_buildargs_returns_none -> PASS")


if __name__ == "__main__":
    print("Running FLOAT_PLAYINGCARD MODULE TESTS...")
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_get_stateful_keys()
    test_buildargs_returns_none()
    print("\nALL TESTS PASSED")