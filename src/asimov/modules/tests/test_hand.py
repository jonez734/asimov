#!/usr/bin/env python3
"""Tests for hand module with mock data."""

import sys
import os
import time
from unittest.mock import patch, MagicMock

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


class MockHandDetector:
    """Mock cvzone HandDetector for testing."""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._hands = []
    
    def findHands(self, frame, draw=True, flipType=False):
        return self._hands, frame
    
    def set_hands(self, hands):
        self._hands = hands


class SimpleContext(dict):
    """Simple dict mock for context."""
    pass


def create_mock_hand(
    lm_list=None,
    fingers=None,
    confidence=0.9,
    bbox=None,
    type="Left",
):
    """Create a mock hand dict matching cvzone output format."""
    hand = {
        "lmList": lm_list or [],
        "bbox": bbox or (0, 0, 0, 0),
        "type": type,
    }
    if confidence is not None:
        hand["confidence"] = confidence
    if fingers is not None:
        hand["fingers"] = fingers
    return hand


# Test cases


def test_detect_creates_hand_context():
    """Test that detect creates HAND context when not present."""
    from asimov.modules import hand
    
    context = SimpleContext()
    frame = MagicMock()
    
    with patch("asimov.modules.hand.HandDetector", MockHandDetector):
        with patch("asimov.modules.hand.conf") as mock_conf:
            mock_conf.get.return_value = {}
            hand.detect(frame, context)
    
    assert "HAND" in context
    assert "detector" in context["HAND"]
    assert "hands" in context["HAND"]
    print("  test_detect_creates_hand_context -> PASS")


def test_detect_finds_hands():
    """Test that detect finds hands in frame."""
    from asimov.modules import hand
    
    context = SimpleContext()
    mock_hand = create_mock_hand(
        lm_list=[[100, 100, 0], [110, 100, 0], [120, 100, 0]],
        confidence=0.9,
    )
    
    class TestDetector:
        def __init__(self, **kwargs):
            self.detectionCon = kwargs.get("detectionCon", 0.6)
            self.maxHands = kwargs.get("maxHands", 1)
        
        def findHands(self, frame, draw=True, flipType=False):
            return [mock_hand], frame
    
    frame = MagicMock()
    
    with patch("asimov.modules.hand.HandDetector", TestDetector):
        with patch("asimov.modules.hand.conf") as mock_conf:
            mock_conf.get.return_value = {}
            hand.detect(frame, context)
    
    assert len(context["HAND"]["hands"]) == 1
    assert context["HAND"]["hands"][0] == mock_hand
    print("  test_detect_finds_hands -> PASS")


def test_detect_no_hands():
    """Test when no hands detected - empty list."""
    from asimov.modules import hand
    
    context = SimpleContext()
    
    class TestDetector:
        def __init__(self, **kwargs):
            pass
        
        def findHands(self, frame, draw=True, flipType=False):
            return [], frame
    
    frame = MagicMock()
    
    with patch("asimov.modules.hand.HandDetector", TestDetector):
        with patch("asimov.modules.hand.conf") as mock_conf:
            mock_conf.get.return_value = {}
            hand.detect(frame, context)
    
    assert context["HAND"]["hands"] == []
    print("  test_detect_no_hands -> PASS")


def test_detect_updates_existing_context():
    """Test that detect updates existing HAND context."""
    from asimov.modules import hand
    
    mock_hand = create_mock_hand()
    mock_detector = MagicMock()
    
    context = SimpleContext({
        "HAND": {
            "detector": mock_detector,
            "hands": [],
            "cfg": {},
            "timestamp": time.time() - 1,
        }
    })
    
    mock_detector.findHands = MagicMock(return_value=([mock_hand], MagicMock()))
    
    frame = MagicMock()
    
    with patch("asimov.modules.hand.conf") as mock_conf:
        mock_conf.get.return_value = {}
        hand.detect(frame, context)
    
    assert len(context["HAND"]["hands"]) == 1
    print("  test_detect_updates_existing_context -> PASS")


def test_draw_returns_frame_when_no_hand():
    """Test draw returns frame unchanged when no HAND context."""
    from asimov.modules import hand
    
    context = SimpleContext()
    frame = MagicMock()
    
    result = hand.draw(frame, context)
    
    assert result is frame
    print("  test_draw_returns_frame_when_no_hand -> PASS")


def test_draw_returns_frame_with_hand():
    """Test draw returns frame with hand overlay."""
    from asimov.modules import hand
    
    context = SimpleContext({
        "HAND": {
            "detector": MagicMock(),
            "hands": [create_mock_hand()],
            "cfg": {"SHOW_LANDMARKS": False},
            "timestamp": time.time(),
        }
    })
    
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    result = hand.draw(frame, context)
    
    assert isinstance(result, np.ndarray)
    print("  test_draw_returns_frame_with_hand -> PASS")


def test_close_cleans_up():
    """Test close cleans up detector resources."""
    from asimov.modules import hand
    
    mock_detector = MagicMock()
    mock_detector.hands = MagicMock()
    
    context = SimpleContext({
        "HAND": {
            "detector": mock_detector,
            "hands": [],
            "cfg": {},
        }
    })
    
    hand.close(None, context=context)
    
    # Should have called hands.close()
    mock_detector.hands.close.assert_called_once()
    print("  test_close_cleans_up -> PASS")


def test_init_returns_true():
    """Test init returns True."""
    from asimov.modules import hand
    
    result = hand.init(None)
    
    assert result is True
    print("  test_init_returns_true -> PASS")


def test_main_returns_true():
    """Test main returns True."""
    from asimov.modules import hand
    
    result = hand.main(None)
    
    assert result is True
    print("  test_main_returns_true -> PASS")


def test_access_returns_true():
    """Test access returns True."""
    from asimov.modules import hand
    
    result = hand.access(None, "run")
    
    assert result is True
    print("  test_access_returns_true -> PASS")


def test_get_stateful_keys():
    """Test get_stateful_keys returns HAND."""
    from asimov.modules import hand
    
    keys = hand.get_stateful_keys()
    
    assert keys == ["HAND"]
    print("  test_get_stateful_keys -> PASS")


def test_ui_schema():
    """Test ui_schema returns valid schema."""
    from asimov.modules import hand
    
    schema = hand.ui_schema()
    
    assert isinstance(schema, dict)
    assert "DETECTION" in schema
    assert "FILTER" in schema
    assert "DRAW" in schema
    print("  test_ui_schema -> PASS")


if __name__ == "__main__":
    print("Running HAND MODULE TESTS...")
    
    test_detect_creates_hand_context()
    test_detect_finds_hands()
    test_detect_no_hands()
    test_detect_updates_existing_context()
    test_draw_returns_frame_when_no_hand()
    test_draw_returns_frame_with_hand()
    test_close_cleans_up()
    test_init_returns_true()
    test_main_returns_true()
    test_access_returns_true()
    test_get_stateful_keys()
    test_ui_schema()
    
    print("\n============================================================")
    print("ALL TESTS PASSED")
    print("============================================================")