"""Evaluate candidate identity fields on TCU Acórdãos rows lacking the official ``KEY``.

#1012 must decide, for the 1992-2016 window, whether some field or composite of fields
(``PROC``, ``NUMACORDAO``, ``ANOACORDAO``, ``COLEGIADO`` and others actually observed) is
unique and stable enough to serve as identity where ``KEY`` does not exist. That decision
needs evidence — null rates and collisions per candidate, measured on real files — not
invention. This module supplies the two pieces ``tcu_acordaos.ingest`` cannot: a loader that
does not demand ``REQUIRED_COLUMNS`` (pre-2017 files lack ``KEY`` by construction, so
``ingest.load_csv`` would reject them outright), and a report of that evidence per candidate.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import tcu_acordaos.ingest  # noqa: F401  (import applies ingest's csv.field_size_limit)


def load_csv_raw(path: Path) -> list[dict[str, str]]:
    """Read an official TCU Acórdãos CSV without validating against REQUIRED_COLUMNS.

    Same pipe-delimited, double-quoted format as ``tcu_acordaos.ingest.load_csv``, but
    intentionally skips its column-presence check so header-incomplete historical files
    (no ``KEY`` before 2017) can still be inspected.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|", quotechar='"')
        return [dict(row) for row in reader]


CandidateFields = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateKeyReport:
    """Null/collision evidence for one candidate identity field or composite."""

    fields: CandidateFields
    total_rows: int
    null_rows: int
    unique_values: int
    colliding_values: int
    max_collision_size: int

    @property
    def is_stable(self) -> bool:
        """True only when every row has the candidate populated and no value collides."""
        return self.null_rows == 0 and self.colliding_values == 0


def _composite_value(row: Mapping[str, str], fields: CandidateFields) -> str | None:
    """Join the candidate's component values, or None if any component is blank."""
    parts: list[str] = []
    for field in fields:
        value = row.get(field, "").strip()
        if not value:
            return None
        parts.append(value)
    return "\x1f".join(parts)


def _evaluate_candidate(
    rows: Sequence[Mapping[str, str]], fields: CandidateFields
) -> CandidateKeyReport:
    values = [_composite_value(row, fields) for row in rows]
    null_rows = sum(1 for v in values if v is None)
    counts = Counter(v for v in values if v is not None)
    colliding_values = sum(1 for count in counts.values() if count > 1)
    max_collision_size = max(counts.values(), default=0)
    return CandidateKeyReport(
        fields=fields,
        total_rows=len(rows),
        null_rows=null_rows,
        unique_values=len(counts),
        colliding_values=colliding_values,
        max_collision_size=max_collision_size,
    )


def analyze_key_candidates(
    rows: Iterable[Mapping[str, str]],
    candidate_fields: Iterable[CandidateFields],
) -> dict[CandidateFields, CandidateKeyReport]:
    """Measure null rate and collisions for each candidate identity field/composite.

    ``candidate_fields`` is a sequence of field-name tuples; a single-field candidate is a
    1-tuple (e.g. ``("NUMACORDAO",)``), a composite candidate has 2+ (e.g.
    ``("PROC", "ANOACORDAO")``). A row missing any component of a composite counts as null
    for that candidate rather than being silently half-keyed.
    """
    candidates = list(candidate_fields)
    if not candidates:
        msg = "candidate_fields must not be empty"
        raise ValueError(msg)
    materialized_rows = list(rows)
    return {fields: _evaluate_candidate(materialized_rows, fields) for fields in candidates}
