"""Compatibility shim for legacy imports."""

from __future__ import annotations

from repo.core import github as _core

__all__ = [name for name in dir(_core) if not name.startswith("__")]

globals().update({name: getattr(_core, name) for name in __all__})
