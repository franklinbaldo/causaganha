"""Compatibility shim for legacy imports."""

from __future__ import annotations

import types

from repo.features import autofix as _autofix

__all__ = [name for name in dir(_autofix) if not name.startswith("__")]

globals().update({name: getattr(_autofix, name) for name in __all__})

if "auto_reply_to_jules" in globals():
    _auto_reply = globals()["auto_reply_to_jules"]
    if isinstance(_auto_reply, types.FunctionType):
        globals()["auto_reply_to_jules"] = types.FunctionType(
            _auto_reply.__code__,
            globals(),
            _auto_reply.__name__,
            _auto_reply.__defaults__,
            _auto_reply.__closure__,
        )
