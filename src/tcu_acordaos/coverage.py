"""Measure the size/cost of expanding TCU Acórdãos ingestion across historical years.

#984 requires measuring cost before broadening coverage beyond the first proven year. This
module turns the official manifest's human-readable sizes (``"489.97 MB"``) into bytes and
sums them across every year TCU actually publishes, so that decision can be made from
observed manifest data rather than a guess.
"""

from __future__ import annotations

import re
from typing import Iterable

from tcu_acordaos.catalog import ManifestEntry

_ACORDAOS_BASE = "Acórdãos"
_UNIT_MULTIPLIERS = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
_SIZE_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>KB|MB|GB)$")


def parse_size_to_bytes(tamanho: str) -> int:
    """Parse a manifest ``TAMANHO`` field such as ``"489.97 MB"`` into a byte count."""
    match = _SIZE_PATTERN.match(tamanho.strip())
    if not match:
        msg = f"unrecognized TCU manifest size: {tamanho!r}"
        raise ValueError(msg)
    value = float(match.group("value"))
    multiplier = _UNIT_MULTIPLIERS[match.group("unit")]
    return round(value * multiplier)


def acordaos_year_entries(entries: Iterable[ManifestEntry]) -> list[ManifestEntry]:
    """Return only Acórdãos entries that carry a year, excluding the cross-year resumo file."""
    return [entry for entry in entries if entry.base == _ACORDAOS_BASE and entry.ano]


def years_available(entries: Iterable[ManifestEntry]) -> list[str]:
    """Return the sorted list of years the official manifest publishes for Acórdãos."""
    return sorted({entry.ano for entry in acordaos_year_entries(entries)})


def total_acordaos_size_bytes(entries: Iterable[ManifestEntry]) -> int:
    """Sum the official manifest's declared size across every Acórdãos year."""
    return sum(parse_size_to_bytes(entry.tamanho) for entry in acordaos_year_entries(entries))
