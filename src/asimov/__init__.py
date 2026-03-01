# asimov/__init__.py
# Backward-compatible shim

# Re-export subpackages for convenience
from . import base
from . import io
from . import net
from . import modules
from . import playingcard

__all__ = ["base", "io", "net", "modules", "playingcard"]
