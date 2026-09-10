"""``IA_UPLOAD_RATE_LIMIT`` must never produce a broken rate limiter.

``archive.py`` builds ``_IA_RATE_LIMITER = AsyncLimiter(max_rate=_ia_max_rate,
time_period=8)`` once at import time from the ``IA_UPLOAD_RATE_LIMIT`` env
var. The existing parsing only guards against non-numeric strings (falls
back to the default of 4 on ``ValueError``), but a numerically valid
non-positive value (``"0"`` or a negative number) sails through untouched.

``AsyncLimiter.acquire(amount=1)`` requires ``0 <= amount <= max_rate`` and
raises ``ValueError`` otherwise — which is unconditionally true whenever
``max_rate <= 0``. That ``acquire()`` call in ``upload_zip`` sits outside its
own try/except (which only wraps the actual IA upload call), and neither
``_process_upload_item`` (catches only ``httpx.HTTPError``/``OSError``) nor
``upload_worker`` catches ``ValueError`` either — so ``IA_UPLOAD_RATE_LIMIT=0``
or a negative value would crash every upload attempt with an unhandled
exception, unlike the already-handled non-numeric-string case.
"""

from __future__ import annotations

from djen_backup.archive import _parse_ia_max_rate


def test_valid_positive_value_is_used() -> None:
    assert _parse_ia_max_rate("8") == 8


def test_missing_value_falls_back_to_default() -> None:
    assert _parse_ia_max_rate(None) == 4


def test_non_numeric_value_falls_back_to_default() -> None:
    assert _parse_ia_max_rate("not-a-number") == 4


def test_zero_falls_back_to_default() -> None:
    """max_rate=0 makes every AsyncLimiter.acquire() call raise ValueError."""
    assert _parse_ia_max_rate("0") == 4


def test_negative_value_falls_back_to_default() -> None:
    """max_rate<0 makes every AsyncLimiter.acquire() call raise ValueError."""
    assert _parse_ia_max_rate("-1") == 4
