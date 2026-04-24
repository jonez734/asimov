#!/usr/bin/env python3
"""Tests for motionblur module."""

import sys
import os

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import motionblur
    assert motionblur.init(None) is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import motionblur
    assert motionblur.main(None) is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import motionblur
    assert motionblur.access(None, "run") is True
    print("  test_access_returns_true -> PASS")


def test_get_stateful_keys():
    """Test get_stateful_keys returns MOTIONBLUR."""
    from asimov.modules import motionblur
    assert motionblur.get_stateful_keys() == ["MOTIONBLUR"]
    print("  test_get_stateful_keys -> PASS")


def test_detect_creates_context():
    """Test detect creates MOTIONBLUR context."""
    from asimov.modules import motionblur
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    context = {}
    motionblur.detect(frame, context)
    assert "MOTIONBLUR" in context
    print("  test_detect_creates_context -> PASS")


def test_draw_returns_frame():
    """Test draw returns frame."""
    from asimov.modules import motionblur
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = motionblur.draw(frame, {})
    assert result is not None
    print("  test_draw_returns_frame -> PASS")


if __name__ == "__main__":
    print("Running MOTIONBLUR MODULE TESTS...")
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_get_stateful_keys()
    test_detect_creates_context()
    test_draw_returns_frame()
    print("\nALL TESTS PASSED")