#!/usr/bin/env python3
"""Tests for facemask module."""

import sys
import os

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import facemask
    assert facemask.init(None) is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import facemask
    assert facemask.main(None) is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import facemask
    assert facemask.access(None, "run") is True
    print("  test_access_returns_true -> PASS")


def test_get_stateful_keys():
    """Test get_stateful_keys returns FACEMASK."""
    from asimov.modules import facemask
    assert facemask.get_stateful_keys() == ["FACEMASK"]
    print("  test_get_stateful_keys -> PASS")


def test_draw_returns_frame():
    """Test draw returns frame."""
    from asimov.modules import facemask
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = facemask.draw(frame, {})
    assert result is not None
    print("  test_draw_returns_frame -> PASS")


if __name__ == "__main__":
    print("Running FACEMASK MODULE TESTS...")
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_get_stateful_keys()
    test_draw_returns_frame()
    print("\nALL TESTS PASSED")