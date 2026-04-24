#!/usr/bin/env python3
"""Tests for get_stateful_keys() in asimov modules."""

import sys
import os

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


def test_hand_get_stateful_keys():
    """Test hand module returns correct stateful keys."""
    from asimov.modules import hand
    
    keys = hand.get_stateful_keys()
    assert keys == ["HAND"], f"Expected ['HAND'], got {keys}"
    print("  hand.get_stateful_keys() -> PASS")


def test_indexfingertip_get_stateful_keys():
    """Test indexfingertip module returns correct stateful keys."""
    from asimov.modules import indexfingertip
    
    keys = indexfingertip.get_stateful_keys()
    assert keys == ["INDEXFINGERTIP"], f"Expected ['INDEXFINGERTIP'], got {keys}"
    print("  indexfingertip.get_stateful_keys() -> PASS")


def test_face_get_stateful_keys():
    """Test face module returns correct stateful keys."""
    from asimov.modules import face
    
    keys = face.get_stateful_keys()
    assert keys == ["FACE"], f"Expected ['FACE'], got {keys}"
    print("  face.get_stateful_keys() -> PASS")


def test_facemask_get_stateful_keys():
    """Test facemask module returns correct stateful keys."""
    from asimov.modules import facemask
    
    keys = facemask.get_stateful_keys()
    assert keys == ["FACEMASK"], f"Expected ['FACEMASK'], got {keys}"
    print("  facemask.get_stateful_keys() -> PASS")


def test_eyes_next_get_stateful_keys():
    """Test eyes_next module returns correct stateful keys."""
    from asimov.modules import eyes_next
    
    keys = eyes_next.get_stateful_keys()
    assert keys == ["EYES"], f"Expected ['EYES'], got {keys}"
    print("  eyes_next.get_stateful_keys() -> PASS")


def test_float_playingcard_get_stateful_keys():
    """Test float_playingcard module returns correct stateful keys."""
    from asimov.modules import float_playingcard
    
    keys = float_playingcard.get_stateful_keys()
    assert keys == ["CARD"], f"Expected ['CARD'], got {keys}"
    print("  float_playingcard.get_stateful_keys() -> PASS")


def test_glitch_get_stateful_keys():
    """Test glitch module returns correct stateful keys."""
    from asimov.modules import glitch
    
    keys = glitch.get_stateful_keys()
    assert keys == ["GLITCH"], f"Expected ['GLITCH'], got {keys}"
    print("  glitch.get_stateful_keys() -> PASS")


def test_motionblur_get_stateful_keys():
    """Test motionblur module returns correct stateful keys."""
    from asimov.modules import motionblur
    
    keys = motionblur.get_stateful_keys()
    assert keys == ["MOTIONBLUR"], f"Expected ['MOTIONBLUR'], got {keys}"
    print("  motionblur.get_stateful_keys() -> PASS")


def test_all_modules_have_get_stateful_keys():
    """Test that all known stateful modules have get_stateful_keys function."""
    from asimov.modules import (
        hand,
        indexfingertip,
        face,
        facemask,
        eyes_next,
        float_playingcard,
        glitch,
        motionblur,
    )
    
    modules = [
        ("hand", hand),
        ("indexfingertip", indexfingertip),
        ("face", face),
        ("facemask", facemask),
        ("eyes_next", eyes_next),
        ("float_playingcard", float_playingcard),
        ("glitch", glitch),
        ("motionblur", motionblur),
    ]
    
    for name, mod in modules:
        assert hasattr(mod, "get_stateful_keys"), f"{name} missing get_stateful_keys"
        assert callable(mod.get_stateful_keys), f"{name}.get_stateful_keys not callable"
    
    print("  All modules have get_stateful_keys() -> PASS")


if __name__ == "__main__":
    print("Running get_stateful_keys() tests...")
    
    test_hand_get_stateful_keys()
    test_indexfingertip_get_stateful_keys()
    test_face_get_stateful_keys()
    test_facemask_get_stateful_keys()
    test_eyes_next_get_stateful_keys()
    test_float_playingcard_get_stateful_keys()
    test_glitch_get_stateful_keys()
    test_motionblur_get_stateful_keys()
    test_all_modules_have_get_stateful_keys()
    
    print("\nAll tests passed!")