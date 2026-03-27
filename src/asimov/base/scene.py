# asimov/scene.py
#
# Procedural scene loader / runner.
# A scene is a lightweight coordinator for modules + config.
#
# Design goals:
# - No classes
# - Hot-reload friendly
# - Works with module.py
# - String module paths allowed
# - Explicit lifecycle, minimal magic

from typing import Any

from asimov.base import module
from asimov import io


# ----------------------------------------------------------------------
# Scene structure (dict-based, intentional)
# ----------------------------------------------------------------------
#
# scene = {
#     "name": str,
#     "modules": [
#         {
#             "name": str,
#             "module": ModuleType,
#             "config": dict,
#         },
#         ...
#     ],
#     "conf": dict,
# }
#


# ----------------------------------------------------------------------
# Load
# ----------------------------------------------------------------------


def load(args: Any, scene_def: dict) -> dict:
    """
    Load and validate a scene definition.

    Resolves module paths, validates lifecycle hooks,
    and returns a fully-loaded scene dict.
    """

    if not isinstance(scene_def, dict):
        raise TypeError("scene_def must be a dict")

    name = scene_def.get("name", "unnamed-scene")
    modules_def = scene_def.get("modules", [])
    conf = scene_def.get("conf", {})

    if not isinstance(modules_def, list):
        raise TypeError("scene['modules'] must be a list")

    loaded_modules = []

    for entry in modules_def:
        if not isinstance(entry, dict):
            raise TypeError("module entry must be a dict")

        mod_name = entry.get("name", "<unnamed>")
        mod_ref = entry.get("module")
        mod_conf = entry.get("conf", {})

        if not mod_ref:
            raise ValueError(f"module entry '{mod_name}' missing 'module'")

        try:
            # Accept string paths OR module objects
            mod = module.get(mod_ref, args)
        except Exception:
            io.echo_traceback(f"scene.load: failed to load module '{mod_name}'")
            raise

        # Validate module lifecycle once
        if module.check(args, mod, op="run", silent=False) is False:
            raise RuntimeError(f"scene.load: module rejected: {mod_name}")

        loaded_modules.append(
            {
                "name": mod_name,
                "module": mod,
                "config": mod_conf,
            }
        )

    scene = {
        "name": name,
        "modules": loaded_modules,
        "conf": conf,
    }

    return scene


# ----------------------------------------------------------------------
# Init
# ----------------------------------------------------------------------


def init(args: Any, scene: dict, **kwargs) -> bool:
    """
    Run init() for all modules in the scene.
    """

    for item in scene["modules"]:
        mod = item["module"]
        try:
            module.runcallback(args, mod.init, optional=True, **kwargs)
        except Exception:
            io.echo_traceback(f"scene.init: init failed in '{item['name']}'")
            return False

    return True


# ----------------------------------------------------------------------
# Main (one-shot lifecycle entry)
# ----------------------------------------------------------------------


def main(args: Any, scene: dict, **kwargs) -> bool:
    """
    Execute full module lifecycle for the scene.
    Intended to be called once.
    """

    for item in scene["modules"]:
        mod = item["module"]
        try:
            if module.run(args, mod, **kwargs) is False:
                io.echo(
                    f"scene.main: module '{item['name']}' returned False",
                    level="error",
                )
                return False
        except Exception:
            io.echo_traceback(f"scene.main: crash in '{item['name']}'")
            return False

    return True


# ----------------------------------------------------------------------
# Access
# ----------------------------------------------------------------------


def access(args: Any, op: str = "run", **kwargs) -> bool:
    """
    Scene-level access gate.
    Currently permissive by design.
    """
    return True


# ----------------------------------------------------------------------
# Utility
# ----------------------------------------------------------------------


def list_modules(scene: dict) -> list[str]:
    """Return module names in load order."""
    return [m["name"] for m in scene.get("modules", [])]


def get_module(scene: dict, name: str):
    """Fetch a module entry by name."""
    for item in scene.get("modules", []):
        if item["name"] == name:
            return item
    return None
