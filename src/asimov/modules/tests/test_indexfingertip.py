#!/usr/bin/env python3
"""Tests for indexfingertip module with mock data."""

import sys
import os
import time
from dataclasses import dataclass, field
from unittest.mock import patch

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


# Mock cvzone HandDetector


class MockHandDetector:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._hands = []

    def findHands(self, frame, draw=True, flipType=False):
        return self._hands, frame

    def set_hands(self, hands):
        self._hands = hands

    def fingersUp(self, hand):
        return hand.get("fingers", [0, 0, 0, 0, 0])


# Mock OneEuroFilter


class MockOneEuroFilter:
    def __init__(self, freq=30, min_cutoff=1.0, beta=0.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.value = 0

    def update(self, value):
        self.value = value
        return value


@dataclass
class TestContext:
    """Thread-safe context mock."""

    _data: dict = field(default_factory=dict)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data


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


def create_mock_hand_ns(hands):
    """Create a mock HAND context namespace."""
    return {
        "hands": hands,
        "detector": MockHandDetector(),
        "cfg": {},
    }


# Test cases


def test_detect_no_hand():
    """Test when no hand is detected - should not be active."""
    from asimov.modules import indexfingertip
    from asimov import conf

    context = TestContext()

    with patch.object(indexfingertip, "conf", conf):
        indexfingertip.detect(None, context)

    # Should create INDEXFINGERTIP but not mark as active
    ns = context.get("INDEXFINGERTIP")
    assert ns is not None
    assert ns.get("active") is False
    print("test_detect_no_hand: PASS")


def test_detect_hand_below_confidence():
    """Test when hand confidence is too low."""
    from asimov.modules import indexfingertip

    context = TestContext()
    hand = create_mock_hand(confidence=0.3)
    context["HAND"] = create_mock_hand_ns([hand])

    # First call creates the INDEXFINGERTIP entry
    indexfingertip.detect(None, context)
    # Second call should detect low confidence
    indexfingertip.detect(None, context)

    ns = context.get("INDEXFINGERTIP")
    assert ns is not None
    assert ns.get("active") is False
    print("test_detect_hand_below_confidence: PASS")


def test_detect_index_finger_up():
    """Test detection when index finger is up."""
    from asimov.modules import indexfingertip

    context = TestContext()
    # lmList with landmark 8 at position (320, 240)
    lm_list = [[0, 0, 0]] * 21  # 21 landmarks
    lm_list[8] = [320, 240, 0]  # landmark 8 = index finger tip

    fingers = [0, 1, 0, 0, 0]  # Only index finger up
    hand = create_mock_hand(lm_list=lm_list, fingers=fingers, confidence=0.9)
    context["HAND"] = create_mock_hand_ns([hand])

    indexfingertip.detect(None, context)

    ns = context.get("INDEXFINGERTIP")
    assert ns is not None
    assert ns.get("active") is True
    assert ns.get("data") is not None
    print("test_detect_index_finger_up: PASS")


def test_detect_index_finger_down():
    """Test that detection fails when index finger is down."""
    from asimov.modules import indexfingertip

    context = TestContext()
    lm_list = [[0, 0, 0]] * 21
    lm_list[8] = [320, 240, 0]

    # Index finger down
    fingers = [0, 0, 0, 0, 0]
    hand = create_mock_hand(lm_list=lm_list, fingers=fingers, confidence=0.9)
    context["HAND"] = create_mock_hand_ns([hand])

    indexfingertip.detect(None, context)

    ns = context.get("INDEXFINGERTIP")
    assert ns is not None
    assert ns.get("active") is False
    print("test_detect_index_finger_down: PASS")


def test_detect_multiple_fingers_up():
    """Test detection works when multiple fingers are up."""
    from asimov.modules import indexfingertip

    context = TestContext()
    lm_list = [[0, 0, 0]] * 21
    lm_list[8] = [320, 240, 0]

    # Index and middle finger up
    fingers = [0, 1, 1, 0, 0]
    hand = create_mock_hand(lm_list=lm_list, fingers=fingers, confidence=0.9)
    context["HAND"] = create_mock_hand_ns([hand])

    indexfingertip.detect(None, context)

    ns = context.get("INDEXFINGERTIP")
    assert ns is not None
    assert ns.get("active") is True
    print("test_detect_multiple_fingers_up: PASS")


def test_draw_inactive():
    """Test draw when not active."""
    import numpy as np
    from asimov.modules import indexfingertip

    context = TestContext()
    context["INDEXFINGERTIP"] = {"active": False, "data": None}

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = indexfingertip.draw(frame, context)

    assert result is not None
    print("test_draw_inactive: PASS")


def test_draw_active():
    """Test draw when active."""
    import numpy as np
    from asimov.modules import indexfingertip

    context = TestContext()
    context["INDEXFINGERTIP"] = {
        "active": True,
        "data": {"x": 320, "y": 240, "timestamp": time.time()},
    }

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = indexfingertip.draw(frame, context)

    assert result is not None
    # Verify circle was drawn (check that pixel at center changed)
    assert result[240, 320, 1] != 0  # green channel
    print("test_draw_active: PASS")


def test_draw_disabled():
    """Test draw when drawing is disabled in config."""
    import numpy as np
    from asimov.modules import indexfingertip
    from asimov import conf

    # Temporarily disable drawing
    original = conf.CONF.get("INDEXFINGERTIP", {}).get("DRAW", {})
    conf.CONF["INDEXFINGERTIP"] = {"DRAW": {"enabled": False}}

    context = TestContext()
    context["INDEXFINGERTIP"] = {
        "active": True,
        "data": {"x": 320, "y": 240, "timestamp": time.time()},
    }

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = indexfingertip.draw(frame, context)

    # Restore original
    conf.CONF["INDEXFINGERTIP"]["DRAW"] = original

    assert result is not None
    print("test_draw_disabled: PASS")


# Run tests


if __name__ == "__main__":
    print("=" * 60)
    print("INDEXFINGERTIP MODULE TESTS")
    print("=" * 60)

    test_detect_no_hand()
    test_detect_hand_below_confidence()
    test_detect_index_finger_up()
    test_detect_index_finger_down()
    test_detect_multiple_fingers_up()
    test_draw_inactive()
    test_draw_active()
    test_draw_disabled()

    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)