#!/usr/bin/env python3
"""Tests for face module."""

import sys
import os

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


class SimpleContext(dict):
    """Simple dict mock for context."""
    pass


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import face
    
    result = face.init(None)
    
    assert result is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import face
    
    result = face.main(None)
    
    assert result is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import face
    
    result = face.access(None, "run")
    
    assert result is True
    print("  test_access_returns_true -> PASS")


def test_get_stateful_keys():
    """Test get_stateful_keys returns FACE."""
    from asimov.modules import face
    
    keys = face.get_stateful_keys()
    
    assert keys == ["FACE"]
    print("  test_get_stateful_keys -> PASS")


def test_ui_schema():
    """Test ui_schema returns valid schema."""
    from asimov.modules import face
    
    schema = face.ui_schema()
    
    assert isinstance(schema, dict)
    print("  test_ui_schema -> PASS")


def test_buildargs_returns_none():
    """Test buildargs returns None."""
    from asimov.modules import face
    
    result = face.buildargs(None)
    
    assert result is None
    print("  test_buildargs_returns_none -> PASS")


def test_draw_returns_frame_when_no_face():
    """Test draw returns frame unchanged when no FACE context."""
    from asimov.modules import face
    
    context = SimpleContext()
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    result = face.draw(frame, context)
    
    assert result is frame
    print("  test_draw_returns_frame_when_no_face -> PASS")


def test_draw_returns_frame_when_disabled():
    """Test draw returns frame when detection disabled."""
    from asimov.modules import face
    
    context = SimpleContext({
        "FACE": {
            "cfg": {"DRAW": {"DETECTION": False}},
            "faces": [],
        }
    })
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    result = face.draw(frame, context)
    
    assert result is frame
    print("  test_draw_returns_frame_when_disabled -> PASS")


if __name__ == "__main__":
    print("Running FACE MODULE TESTS...")
    
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_get_stateful_keys()
    test_ui_schema()
    test_buildargs_returns_none()
    test_draw_returns_frame_when_no_face()
    test_draw_returns_frame_when_disabled()
    
    print("\n============================================================")
    print("ALL TESTS PASSED")
    print("============================================================")