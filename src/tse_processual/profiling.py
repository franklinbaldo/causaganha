"""Exact relational profiling for acquired TSE Processual CSV archives.

The schema inspector deliberately stops at candidate key names. This module is
the next evidence layer: it scans the complete official CSVs, measures key
cardinality and orphan joins, and reports CNJ-shaped values without promoting
any candidate to product identity.
"""

from __future__ import annotations

import csv
import io
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from zipfile import ZipFile

from causaganha.processos.cnj import validar_digito_verificador
from tse_processual.inspection import CsvInspection, common_process_keys, inspect_zip

if TYPE_CHECKING:
    from collections.abc import Mapping

_RESOURCE_ORDER = ("processos", "assuntos", "decisoes")
_CNJ_PRESENTATION = re.compile(r"[0-9.\-/\s]+")
_NON_DIGITS = re.compile(r"\D+")
_CREATE_TABLE_SQL = {
    "processos": 'CREATE TABLE "processos" (value TEXT PRIMARY KEY)',
    "assuntos": 'CREATE TABLE "assuntos" (value TEXT PRIMARY KEY)',
    "decisoes": 'CREATE TABLE "decisoes" (value TEXT PRIMARY KEY)',
}
_INSERT_SQL = {
    "processos": 'INSERT OR IGNORE INTO "processos" (value) VALUES (?)',
    "assuntos": 'INSERT OR IGNORE INTO "assuntos" (value) VALUES (?)',
    "decisoes": 'INSERT OR IGNORE INTO "decisoes" (value) VALUES (?)',
}
_COUNT_SQL = {
    "processos": 'SELECT COUNT(*) FROM "processos"',
    "assuntos": 'SELECT COUNT(*) FROM "assuntos"',
    "decisoes": 'SELECT COUNT(*) FROM "decisoes"',
}
_CHILD_JOIN_SQL = {
    "assuntos": (
        'SELECT COUNT(*) FROM "assuntos" AS c INNER JOIN "processos" AS p ON p.value = c.value'
    ),
    "decisoes": (
        'SELECT COUNT(*) FROM "decisoes" AS c INNER JOIN "processos" AS p ON p.value = c.value'
    ),
}


@dataclass(frozen=True, slots=True)
class KeyStats:
    """Exact row/cardinality evidence for one candidate key in one resource."""

    rows: int
    null_rows: int
    non_null_rows: int
    distinct_values: int
    duplicate_rows: int
    cnj_shaped_rows: int
    cnj_valid_rows: int

    @property
    def unique_when_present(self) -> bool:
        """Whether every non-null key value occurs at most once."""
        return self.non_null_rows == self.distinct_values


@dataclass(frozen=True, slots=True)
class ChildJoinStats:
    """Distinct-key join evidence from one child resource to Processos."""

    distinct_values: int
    matched_processos_distinct: int
    orphan_distinct: int

    @property
    def distinct_coverage(self) -> float | None:
        """Share of child distinct keys found in Processos."""
        if self.distinct_values == 0:
            return None
        return self.matched_processos_distinct / self.distinct_values


def _actual_column(inspection: CsvInspection, normalized: str) -> str:
    for column in inspection.columns:
        if column.strip().upper() == normalized:
            return column
    msg = f"candidate column {normalized!r} not found in {inspection.archive}"
    raise ValueError(msg)


def _cnj_shaped(value: str) -> bool:
    """Return whether a value is composed only of a 20-digit CNJ presentation."""
    if _CNJ_PRESENTATION.fullmatch(value) is None:
        return False
    return len(_NON_DIGITS.sub("", value)) == 20


def _load_distinct_keys(
    connection: sqlite3.Connection,
    *,
    table: str,
    path: Path,
    inspection: CsvInspection,
    candidate: str,
) -> KeyStats:
    connection.execute(_CREATE_TABLE_SQL[table])
    actual_column = _actual_column(inspection, candidate)
    rows = 0
    null_rows = 0
    non_null_rows = 0
    cnj_shaped_rows = 0
    cnj_valid_rows = 0

    with ZipFile(path) as archive, archive.open(inspection.member) as raw:
        with io.TextIOWrapper(raw, encoding=inspection.encoding, newline="") as text:
            reader = csv.DictReader(text, delimiter=inspection.delimiter)
            cursor = connection.cursor()
            try:
                for row in reader:
                    rows += 1
                    value = str(row.get(actual_column) or "").strip()
                    if not value:
                        null_rows += 1
                        continue
                    non_null_rows += 1
                    if _cnj_shaped(value):
                        cnj_shaped_rows += 1
                        if validar_digito_verificador(value):
                            cnj_valid_rows += 1
                    cursor.execute(_INSERT_SQL[table], (value,))
            finally:
                cursor.close()

    distinct_values = int(connection.execute(_COUNT_SQL[table]).fetchone()[0])
    return KeyStats(
        rows=rows,
        null_rows=null_rows,
        non_null_rows=non_null_rows,
        distinct_values=distinct_values,
        duplicate_rows=non_null_rows - distinct_values,
        cnj_shaped_rows=cnj_shaped_rows,
        cnj_valid_rows=cnj_valid_rows,
    )


def _child_join_stats(connection: sqlite3.Connection, child: str) -> ChildJoinStats:
    distinct_values = int(connection.execute(_COUNT_SQL[child]).fetchone()[0])
    matched = int(connection.execute(_CHILD_JOIN_SQL[child]).fetchone()[0])
    return ChildJoinStats(
        distinct_values=distinct_values,
        matched_processos_distinct=matched,
        orphan_distinct=distinct_values - matched,
    )


def profile_candidate_key(
    resources: Mapping[str, Path],
    inspections: Mapping[str, CsvInspection],
    candidate: str,
) -> dict[str, object]:
    """Profile one common candidate key over all complete CSV resources."""
    missing = [name for name in _RESOURCE_ORDER if name not in resources or name not in inspections]
    if missing:
        msg = f"missing required resources for relational profile: {missing!r}"
        raise ValueError(msg)

    with TemporaryDirectory(prefix="causaganha-tse-profile-") as temporary:
        connection = sqlite3.connect(Path(temporary) / "keys.sqlite3")
        try:
            stats = {
                name: _load_distinct_keys(
                    connection,
                    table=name,
                    path=resources[name],
                    inspection=inspections[name],
                    candidate=candidate,
                )
                for name in _RESOURCE_ORDER
            }
            connection.commit()
            child_joins = {
                name: _child_join_stats(connection, name) for name in ("assuntos", "decisoes")
            }
        finally:
            connection.close()

    processos = stats["processos"]
    relational_shape_supported = (
        processos.null_rows == 0
        and processos.unique_when_present
        and all(join.orphan_distinct == 0 for join in child_joins.values())
    )
    return {
        "candidate": candidate,
        "resources": {
            name: asdict(value) | {"unique_when_present": value.unique_when_present}
            for name, value in stats.items()
        },
        "child_joins_to_processos": {
            name: asdict(value) | {"distinct_coverage": value.distinct_coverage}
            for name, value in child_joins.items()
        },
        "relational_shape_supported": relational_shape_supported,
        "identity_proven": False,
        "cnj_note": (
            "cnj_shaped_rows only checks a 20-digit CNJ presentation. "
            "cnj_valid_rows additionally validates the check digit (Resolução "
            "CNJ 65/2008 art. 4º), but a valid check digit alone still does "
            "not prove product identity with another dataset."
        ),
    }


def relational_profile(resources: Mapping[str, Path]) -> dict[str, object]:
    """Measure every observed common process-key candidate on complete CSVs."""
    missing = [name for name in _RESOURCE_ORDER if name not in resources]
    if missing:
        msg = f"missing required resources: {missing!r}"
        raise ValueError(msg)

    inspections = {name: inspect_zip(resources[name]) for name in _RESOURCE_ORDER}
    candidates = common_process_keys(inspections.values())
    profiles = [
        profile_candidate_key(resources, inspections, candidate) for candidate in candidates
    ]
    return {
        "resources": {name: asdict(inspection) for name, inspection in inspections.items()},
        "candidate_profiles": profiles,
        "identity_proven": False,
        "identity_note": (
            "A relational shape can support an identity hypothesis, but promotion still "
            "requires documented semantic evidence and comparison against an external "
            "canonical identity."
        ),
    }
