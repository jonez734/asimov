# asimov/scene.py
#
# Procedural scene manager for Asimov
#
# Responsibilities:
#   - atomic scene switching at frame boundaries
#   - reversible per-scene conf overrides
#   - explicit lifecycle (init / shutdown)
#
# Non-goals:
#   - no threading owned by scenes
#   - no background mutation of conf
#   - no module reload magic
#

import threading
from copy import deepcopy
from asimov import conf

# ------------------------------------------------------------
# Global scene state
# ------------------------------------------------------------

_active_scene = None       # currently running scene dict
_pending_scene = None      # scene requested for next frame
_lock = threading.Lock()   # protects _pending_scene swap

# stack of previous conf snapshots (LIFO)
_conf_stack = []

# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def request(scene: dict):
    """
    Request a scene change.
    Safe to call from any thread.
    """
    global _pending_scene
    with _lock:
        _pending_scene = scene


def apply_if_needed(*, args, context):
    """
    Apply a pending scene change.
    MUST be called from the main frame loop.
    """
    global _active_scene, _pending_scene

    if _pending_scene is None:
        return

    with _lock:
        # --- shutdown old scene ---
        if _active_scene:
            shutdown = _active_scene.get("shutdown")
            if callable(shutdown):
                shutdown(context=context)

            _restore_conf()

        # --- reset shared state ---
        context.reset()

        # --- activate new scene ---
        _active_scene = _pending_scene
        _pending_scene = None

        # --- apply scene conf overrides ---
        overrides = _active_scene.get("conf")
        if overrides:
            _apply_conf_overrides(overrides)

        # --- init new scene ---
        init = _active_scene.get("init")
        if callable(init):
            init(args=args, context=context)


def active_modules():
    """
    Return modules for the active scene.
    """
    if not _active_scene:
        return []
    return _active_scene.get("modules", [])


def active_name():
    """
    Return name of active scene or None.
    """
    if not _active_scene:
        return None
    return _active_scene.get("name")


# ------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------

def _apply_conf_overrides(overrides: dict):
    """
    Apply per-scene configuration overrides.
    Stores a deep snapshot for later restoration.
    """
    snapshot = {}

    for section, values in overrides.items():
        if not hasattr(conf, section):
            raise KeyError(f"conf.{section} does not exist")

        original = getattr(conf, section)

        if not isinstance(original, dict):
            raise TypeError(
                f"conf.{section} must be a dict for scene overrides"
            )

        snapshot[section] = deepcopy(original)
        original.update(values)

    _conf_stack.append(snapshot)


def _restore_conf():
    """
    Restore configuration to the state prior to the last override.
    """
    if not _conf_stack:
        return

    snapshot = _conf_stack.pop()

    for section, original in snapshot.items():
        setattr(conf, section, original)
