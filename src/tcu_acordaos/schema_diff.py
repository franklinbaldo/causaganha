"""Compare an observed TCU Acórdãos CSV header against the documented product contract.

#984 requires mapping the schema observed in a real bulk file against the dictionary
line-by-line, without inventing fields that aren't there or silently dropping ones that are.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tcu_acordaos.ingest import REQUIRED_COLUMNS


@dataclass(frozen=True, slots=True)
class SchemaDiff:
    """Gap between an observed CSV header and the columns the product requires."""

    missing: tuple[str, ...]
    extra: tuple[str, ...]

    @property
    def is_compatible(self) -> bool:
        return not self.missing


def diff_header(observed: Iterable[str]) -> SchemaDiff:
    """Diff ``observed`` column names against ``ingest.REQUIRED_COLUMNS``.

    ``missing`` lists required columns absent from ``observed`` (this is what would make
    ingestion fail); ``extra`` lists observed columns the product doesn't use yet, surfaced
    for visibility rather than dropped silently.
    """
    observed_set = set(observed)
    missing = tuple(sorted(REQUIRED_COLUMNS - observed_set))
    extra = tuple(sorted(observed_set - REQUIRED_COLUMNS))
    return SchemaDiff(missing=missing, extra=extra)
