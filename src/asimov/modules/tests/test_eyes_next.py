#!/usr/bin/env python3
"""Tests for eyes_next module."""

import sys
import os
import time

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


class SimpleContext(dict):
    """Simple dict mock for context."""

    pass


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import eyes_next

    result = eyes_next.init(None)
    assert result is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import eyes_next

    result = eyes_next.main(None)
    assert result is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import eyes_next

    result = eyes_next.access(None, "run")
    assert result is True
    print("  test_access_returns_true -> PASS")


def test_get_stateful_keys():
    """Test get_stateful_keys returns EYES."""
    from asimov.modules import eyes_next

    keys = eyes_next.get_stateful_keys()
    assert keys == ["EYES"]
    print("  test_get_stateful_keys -> PASS")


def test_ui_schema():
    """Test ui_schema returns valid schema."""
    from asimov.modules import eyes_next

    schema = eyes_next.ui_schema()
    assert isinstance(schema, dict)
    print("  test_ui_schema -> PASS")


def test_buildargs_returns_none():
    """Test buildargs returns None."""
    from asimov.modules import eyes_next

    result = eyes_next.buildargs(None)
    assert result is None
    print("  test_buildargs_returns_none -> PASS")


def test_get_conf_returns_eyes_dict():
    """Test _get_conf returns EYES config dict from global conf."""
    from asimov.modules import eyes_next

    result = eyes_next._get_conf(None)
    assert isinstance(result, dict)
    assert "FILTER" in result
    assert "BAR" in result
    print("  test_get_conf_returns_eyes_dict -> PASS")


def test_get_conf_with_scene_conf():
    """Test _get_conf extracts EYES from scene conf dict."""
    from asimov.modules import eyes_next

    scene_conf = {"EYES": {"FILTER": {"FREQ": 30.0}}}
    result = eyes_next._get_conf(scene_conf)
    assert result is not None
    assert result["FILTER"]["FREQ"] == 30.0
    print("  test_get_conf_with_scene_conf -> PASS")


def test_draw_returns_frame_when_no_eyes():
    """Test draw returns frame unchanged when no EYES context."""
    from asimov.modules import eyes_next

    context = SimpleContext()
    import numpy as np

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = eyes_next.draw(frame, context)

    assert result is frame
    print("  test_draw_returns_frame_when_no_eyes -> PASS")


def test_draw_returns_frame_when_no_data():
    """Test draw returns frame when EYES exists but no data."""
    from asimov.modules import eyes_next

    context = SimpleContext({"EYES": {"data": None}})
    import numpy as np

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = eyes_next.draw(frame, context)

    assert result is frame
    print("  test_draw_returns_frame_when_no_data -> PASS")


def test_render_layer_returns_none_when_no_eyes():
    """Test render_layer returns None when no EYES context."""
    from asimov.modules import eyes_next

    context = SimpleContext()

    result = eyes_next.render_layer(context, (480, 640))

    assert result is None
    print("  test_render_layer_returns_none_when_no_eyes -> PASS")


def test_render_layer_returns_layer_with_data():
    """Test render_layer returns RGBA layer when EYES data exists."""
    from asimov.modules import eyes_next

    now = time.time()
    context = SimpleContext(
        {
            "EYES": {
                "data": {
                    "cx": 320.0,
                    "cy": 240.0,
                    "w": 100.0,
                    "h": 50.0,
                    "angle": 0.0,
                    "timestamp": now,
                }
            }
        }
    )

    result = eyes_next.render_layer(context, (480, 640))

    assert result is not None
    import numpy as np

    assert result.shape == (480, 640, 4)
    assert result.dtype == np.uint8
    print("  test_render_layer_returns_layer_with_data -> PASS")


def test_expire_bar_clears_old_data():
    """Test _expire_bar clears data when grace period exceeded."""
    from asimov.modules import eyes_next

    old_timestamp = time.time() - 1.0
    ns = {"data": {"timestamp": old_timestamp}}

    conf = {"BAR": {"GRACE_PERIOD": 0.35}}
    eyes_next._expire_bar(ns, conf)

    assert ns["data"] is None
    print("  test_expire_bar_clears_old_data -> PASS")


def test_expire_bar_keeps_fresh_data():
    """Test _expire_bar keeps data when within grace period."""
    from asimov.modules import eyes_next

    now = time.time()
    ns = {"data": {"timestamp": now}}

    conf = {"BAR": {"GRACE_PERIOD": 0.35}}
    eyes_next._expire_bar(ns, conf)

    assert ns["data"] is not None
    print("  test_expire_bar_keeps_fresh_data -> PASS")


def test_detect_with_no_face():
    """Test detect returns without error when no FACE in context."""
    from asimov.modules import eyes_next

    context = SimpleContext()
    import numpy as np

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result = eyes_next.detect(frame, context)

    assert result is None
    print("  test_detect_with_no_face -> PASS")


def test_update_with_no_face():
    """Test scene update returns without error when no FACE."""
    from asimov.modules import eyes_next

    context = SimpleContext()

    result = eyes_next.update(context)

    assert result is None
    print("  test_update_with_no_face -> PASS")


if __name__ == "__main__":
    print("Running EYES_NEXT MODULE TESTS...")
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_get_stateful_keys()
    test_ui_schema()
    test_buildargs_returns_none()
    test_get_conf_returns_eyes_dict()
    test_get_conf_with_scene_conf()
    test_draw_returns_frame_when_no_eyes()
    test_draw_returns_frame_when_no_data()
    test_render_layer_returns_none_when_no_eyes()
    test_render_layer_returns_layer_with_data()
    test_expire_bar_clears_old_data()
    test_expire_bar_keeps_fresh_data()
    test_detect_with_no_face()
    test_update_with_no_face()
    print("\n============================================================")
    print("ALL TESTS PASSED")
    print("============================================================")
