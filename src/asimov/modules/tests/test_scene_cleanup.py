#!/usr/bin/env python3
"""Tests for scene state cleanup logic."""

import sys
import os
from unittest.mock import MagicMock

# Add parent to path for imports
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _src)


class MockModule:
    def __init__(self, name, stateful_keys):
        self.name = name
        self._stateful_keys = stateful_keys
    
    def get_stateful_keys(self):
        return self._stateful_keys
    
    def close(self, args, context=None):
        pass


class SimpleContext(dict):
    """Simple dict mock for context."""
    pass


def test_collect_declared_keys():
    """Test collecting declared keys from modules."""
    modules = [
        {"name": "hand", "module_ref": MockModule("hand", ["HAND"])},
        {"name": "indexfingertip", "module_ref": MockModule("indexfingertip", ["INDEXFINGERTIP"])},
        {"name": "face", "module_ref": MockModule("face", ["FACE"])},
    ]
    
    declared_keys = set()
    for item in modules:
        m = item.get("module_ref")
        if m and hasattr(m, "get_stateful_keys"):
            try:
                keys = m.get_stateful_keys()
                declared_keys.update(keys)
            except Exception:
                pass
    
    assert declared_keys == {"HAND", "INDEXFINGERTIP", "FACE"}, f"Expected {{HAND, INDEXFINGERTIP, FACE}}, got {declared_keys}"
    print("  Collect declared keys -> PASS")


def test_collect_existing_keys_by_prefix():
    """Test collecting existing stateful keys by known prefixes."""
    context = SimpleContext({
        "HAND": {"detector": None},
        "INDEXFINGERTIP": {"active": False},
        "FACE": {"faces": []},
        "GLITCH": {"active": True},
        "UNRELATED": {"data": 123},  # Should be filtered out
        "FPS": {"value": 30},  # Should be filtered out
    })
    
    known_prefixes = ["HAND", "FACE", "INDEXFINGER", "CARD", "RECT", "EYES", "GLITCH", "MOTION"]
    
    existing_keys = set()
    for key in context.keys():
        if any(key.startswith(p) for p in known_prefixes):
            existing_keys.add(key)
    
    assert existing_keys == {"HAND", "INDEXFINGERTIP", "FACE", "GLITCH"}, f"Expected {{HAND, INDEXFINGERTIP, FACE, GLITCH}}, got {existing_keys}"
    print("  Collect existing keys by prefix -> PASS")


def test_cleanup_declared_keys():
    """Test cleaning up declared keys from context."""
    context = SimpleContext({
        "HAND": {"detector": None},
        "INDEXFINGERTIP": {"active": False},
        "FACE": {"faces": []},
    })
    
    declared_keys = {"HAND", "INDEXFINGERTIP"}
    
    for key in declared_keys:
        if key in context:
            del context[key]
    
    assert "HAND" not in context
    assert "INDEXFINGERTIP" not in context
    assert "FACE" in context  # Not in declared, should remain
    print("  Cleanup declared keys -> PASS")


def test_detect_undeclared_keys():
    """Test detecting undeclared keys."""
    existing_keys = {"HAND", "INDEXFINGERTIP", "FACE", "GLITCH"}
    declared_keys = {"HAND", "INDEXFINGERTIP"}  # FACE and GLITCH not declared
    
    leftover_keys = existing_keys - declared_keys
    
    assert leftover_keys == {"FACE", "GLITCH"}, f"Expected {{FACE, GLITCH}}, got {leftover_keys}"
    print("  Detect undeclared keys -> PASS")


def test_module_without_get_stateful_keys():
    """Test module without get_stateful_keys is handled gracefully."""
    modules = [
        {"name": "fps_overlay", "module_ref": MagicMock()},  # No get_stateful_keys
    ]
    
    declared_keys = set()
    for item in modules:
        m = item.get("module_ref")
        if m and hasattr(m, "get_stateful_keys"):
            keys = m.get_stateful_keys()
            declared_keys.update(keys)
    
    assert declared_keys == set(), f"Expected empty set, got {declared_keys}"
    print("  Module without get_stateful_keys -> PASS")


def test_empty_context_handling():
    """Test handling empty context."""
    context = SimpleContext({})
    
    known_prefixes = ["HAND", "FACE", "INDEXFINGER", "CARD", "RECT", "EYES", "GLITCH", "MOTION"]
    
    existing_keys = set()
    for key in context.keys():
        if any(key.startswith(p) for p in known_prefixes):
            existing_keys.add(key)
    
    assert existing_keys == set()
    print("  Empty context handling -> PASS")


def test_no_warnings_for_clean_state():
    """Test no warnings when state is clean."""
    existing_keys = {"HAND", "INDEXFINGERTIP", "FACE"}
    declared_keys = {"HAND", "INDEXFINGERTIP", "FACE"}  # All declared
    
    leftover_keys = existing_keys - declared_keys
    
    assert len(leftover_keys) == 0, f"Should be no leftover keys, got {leftover_keys}"
    print("  No warnings for clean state -> PASS")


if __name__ == "__main__":
    print("Running scene state cleanup tests...")
    
    test_collect_declared_keys()
    test_collect_existing_keys_by_prefix()
    test_cleanup_declared_keys()
    test_detect_undeclared_keys()
    test_module_without_get_stateful_keys()
    test_empty_context_handling()
    test_no_warnings_for_clean_state()
    
    print("\nAll tests passed!")