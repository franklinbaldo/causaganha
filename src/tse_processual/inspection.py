"""Schema inspection for official TSE Processual ZIP resources.

This module is deliberately evidence-first: it reports what the CSVs actually
contain without assigning product semantics to undocumented columns.  It is a
small bridge between the acquisition boundary and the identity/join proof in
issue #985.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

if TYPE_CHECKING:
    from collections.abc import Iterable

_SAMPLE_BYTES = 64 * 1024
_CANDIDATE_KEY_PRIORITY = (
    "SQ_PROCESSO",
    "ID_PROCESSO",
    "NR_PROCESSO",
    "NUMERO_PROCESSO",
    "NUM_PROCESSO",
)
_GENERATION_DATE_COLUMNS = ("DT_GERACAO", "DATA_GERACAO", "DT_EXTRACAO", "DATA_EXTRACAO")
_GENERATION_TIME_COLUMNS = ("HH_GERACAO", "HORA_GERACAO", "HH_EXTRACAO", "HORA_EXTRACAO")


class InvalidProcessualArchiveError(ValueError):
    """Raised when an acquired ZIP does not expose one inspectable CSV."""


@dataclass(frozen=True, slots=True)
class CsvInspection:
    """Observed schema/provenance facts for one CSV inside an official ZIP."""

    archive: str
    member: str
    encoding: str
    delimiter: str
    columns: tuple[str, ...]
    sampled_rows: int
    generation_date_column: str | None
    generation_time_column: str | None
    generation_date_values: tuple[str, ...]
    generation_time_values: tuple[str, ...]

    @property
    def normalized_columns(self) -> tuple[str, ...]:
        """Column names normalized only for cross-resource comparison."""
        return tuple(column.strip().upper() for column in self.columns)


def _csv_member(archive: ZipFile) -> str:
    members = [
        name
        for name in archive.namelist()
        if not name.endswith("/") and name.lower().endswith(".csv")
    ]
    if len(members) != 1:
        msg = f"expected exactly one CSV member, found {len(members)}: {members!r}"
        raise InvalidProcessualArchiveError(msg)
    return members[0]


def _detect_encoding(sample: bytes) -> str:
    try:
        sample.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "latin-1"
    return "utf-8-sig"


def _detect_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text, delimiters=";,").delimiter
    except csv.Error as exc:
        msg = "could not determine CSV delimiter from official resource"
        raise InvalidProcessualArchiveError(msg) from exc


def _find_column(columns: Iterable[str], candidates: tuple[str, ...]) -> str | None:
    by_normalized = {column.strip().upper(): column for column in columns}
    for candidate in candidates:
        if candidate in by_normalized:
            return by_normalized[candidate]
    return None


def inspect_zip(path: Path, *, sample_rows: int = 1000) -> CsvInspection:
    """Inspect one official ZIP without loading the whole CSV into memory.

    The function observes encoding, delimiter, header and extraction/generation
    metadata values from a bounded prefix.  `sample_rows` controls only the
    evidence sample and never changes the detected header.
    """
    if sample_rows < 1:
        msg = "sample_rows must be at least 1"
        raise ValueError(msg)

    with ZipFile(path) as archive:
        member = _csv_member(archive)
        with archive.open(member) as raw:
            sample = raw.read(_SAMPLE_BYTES)

        encoding = _detect_encoding(sample)
        sample_text = sample.decode(encoding)
        delimiter = _detect_delimiter(sample_text)

        with archive.open(member) as raw:
            text = (line.decode(encoding) for line in raw)
            reader = csv.DictReader(text, delimiter=delimiter)
            if reader.fieldnames is None:
                msg = f"CSV member has no header: {member}"
                raise InvalidProcessualArchiveError(msg)

            columns = tuple(reader.fieldnames)
            date_column = _find_column(columns, _GENERATION_DATE_COLUMNS)
            time_column = _find_column(columns, _GENERATION_TIME_COLUMNS)
            date_values: set[str] = set()
            time_values: set[str] = set()
            sampled = 0
            for row in reader:
                sampled += 1
                if date_column and row.get(date_column):
                    date_values.add(str(row[date_column]).strip())
                if time_column and row.get(time_column):
                    time_values.add(str(row[time_column]).strip())
                if sampled >= sample_rows:
                    break

    return CsvInspection(
        archive=path.name,
        member=member,
        encoding=encoding,
        delimiter=delimiter,
        columns=columns,
        sampled_rows=sampled,
        generation_date_column=date_column,
        generation_time_column=time_column,
        generation_date_values=tuple(sorted(value for value in date_values if value)),
        generation_time_values=tuple(sorted(value for value in time_values if value)),
    )


def common_process_keys(inspections: Iterable[CsvInspection]) -> tuple[str, ...]:
    """Return observed process-shaped columns shared by every resource.

    This is intentionally a candidate report, not an identity claim.  A key
    only becomes authoritative after uniqueness/cardinality are measured on
    the real files.
    """
    normalized = [set(inspection.normalized_columns) for inspection in inspections]
    if not normalized:
        return ()
    common = set.intersection(*normalized)
    ordered = [name for name in _CANDIDATE_KEY_PRIORITY if name in common]
    other = sorted(name for name in common if "PROCESS" in name and name not in ordered)
    return tuple([*ordered, *other])


def inspection_report(paths: Iterable[Path], *, sample_rows: int = 1000) -> dict[str, object]:
    """Build a machine-readable report for a set of acquired official ZIPs."""
    inspections = tuple(inspect_zip(path, sample_rows=sample_rows) for path in paths)
    return {
        "resources": [asdict(inspection) for inspection in inspections],
        "common_process_key_candidates": list(common_process_keys(inspections)),
        "identity_proven": False,
        "identity_note": (
            "Candidate columns are observational only; prove uniqueness and join cardinality "
            "on the complete official CSVs before promoting any key to product identity."
        ),
    }


def write_inspection_report(
    paths: Iterable[Path], destination: Path, *, sample_rows: int = 1000
) -> None:
    """Write the deterministic inspection report as UTF-8 JSON."""
    report = inspection_report(paths, sample_rows=sample_rows)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
