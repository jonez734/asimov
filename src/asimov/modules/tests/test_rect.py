#!/usr/bin/env python3
"""Tests for rect module."""

import sys
import os

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


def test_point_in_rect():
    """Test point in rect detection."""
    from asimov.modules.rect import _point_in_rect
    
    rect = {"x": 10, "y": 10, "w": 100, "h": 50}
    assert _point_in_rect((50, 30), rect) is True
    assert _point_in_rect((5, 5), rect) is False
    print("  test_point_in_rect -> PASS")


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import rect
    assert rect.init(None) is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import rect
    assert rect.main(None) is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import rect
    assert rect.access(None, "run") is True
    print("  test_access_returns_true -> PASS")


def test_buildargs_returns_none():
    """Test buildargs returns None."""
    from asimov.modules import rect
    assert rect.buildargs(None) is None
    print("  test_buildargs_returns_none -> PASS")


if __name__ == "__main__":
    print("Running RECT MODULE TESTS...")
    test_point_in_rect()
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_buildargs_returns_none()
    print("\nALL TESTS PASSED")