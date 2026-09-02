"""Deterministic ingestion contract for the official TCU Acórdãos CSV export.

This module intentionally does not discover or scrape download URLs. Acquisition is a
separate concern: callers provide a CSV already obtained from the TCU open-data portal
and explicit provenance for that byte stream.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

_FIELD_SIZE_LIMIT = 10 * 1024 * 1024
"""Some official VOTO/ACORDAO fields exceed csv's 128 KiB default, observed live 2026-09-02."""
csv.field_size_limit(_FIELD_SIZE_LIMIT)

REQUIRED_COLUMNS = frozenset(
    {
        "KEY",
        "TIPO",
        "TITULO",
        "NUMACORDAO",
        "ANOACORDAO",
        "COLEGIADO",
        "DATASESSAO",
        "RELATOR",
        "SITUACAO",
        "PROC",
        "ASSUNTO",
        "SUMARIO",
        "ACORDAO",
        "DECISAO",
        "RELATORIO",
        "VOTO",
    }
)


@dataclass(frozen=True, slots=True)
class AcquisitionProvenance:
    """Evidence that identifies the exact official bulk file used as input."""

    source_url: str
    acquired_at: str
    sha256: str

    @classmethod
    def from_file(
        cls,
        path: Path,
        *,
        source_url: str,
        acquired_at: str,
    ) -> AcquisitionProvenance:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return cls(source_url=source_url, acquired_at=acquired_at, sha256=digest)


@dataclass(frozen=True, slots=True)
class AcordaoRecord:
    """Small, loss-aware product view over one official TCU Acórdão row."""

    key: str
    numero: str
    ano: str
    colegiado: str
    processo: str
    data_sessao: str
    relator: str
    situacao: str
    titulo: str
    assunto: str
    sumario: str
    acordao: str
    decisao: str
    relatorio: str
    voto: str
    source_url: str
    acquired_at: str
    source_sha256: str


def canonical_key(row: Mapping[str, str]) -> str:
    """Return the TCU-provided unique key; never synthesize identity from display fields."""
    key = row.get("KEY", "").strip()
    if not key:
        msg = "TCU Acórdãos row is missing the official KEY identifier"
        raise ValueError(msg)
    return key


def _validate_columns(fieldnames: Iterable[str] | None) -> None:
    observed = set(fieldnames or ())
    missing = REQUIRED_COLUMNS - observed
    if missing:
        rendered = ", ".join(sorted(missing))
        msg = f"TCU Acórdãos CSV is missing documented columns: {rendered}"
        raise ValueError(msg)


def load_csv(path: Path) -> list[dict[str, str]]:
    """Load an official TCU Acórdãos CSV without guessing absent schema fields.

    The official bulk export is pipe-delimited with double-quoted fields, not comma-delimited
    — confirmed live across sampled years 1992-2026 on 2026-09-02 (see docs/data/tcu-acordaos.md).
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|", quotechar='"')
        _validate_columns(reader.fieldnames)
        return [dict(row) for row in reader]


def transform_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    provenance: AcquisitionProvenance,
) -> list[AcordaoRecord]:
    """Build a deterministic product view while retaining primary-source provenance."""
    records: list[AcordaoRecord] = []
    seen: set[str] = set()
    for row in rows:
        key = canonical_key(row)
        if key in seen:
            msg = f"duplicate official TCU KEY in input: {key}"
            raise ValueError(msg)
        seen.add(key)
        records.append(
            AcordaoRecord(
                key=key,
                numero=row.get("NUMACORDAO", "").strip(),
                ano=row.get("ANOACORDAO", "").strip(),
                colegiado=row.get("COLEGIADO", "").strip(),
                processo=row.get("PROC", "").strip(),
                data_sessao=row.get("DATASESSAO", "").strip(),
                relator=row.get("RELATOR", "").strip(),
                situacao=row.get("SITUACAO", "").strip(),
                titulo=row.get("TITULO", "").strip(),
                assunto=row.get("ASSUNTO", "").strip(),
                sumario=row.get("SUMARIO", "").strip(),
                acordao=row.get("ACORDAO", "").strip(),
                decisao=row.get("DECISAO", "").strip(),
                relatorio=row.get("RELATORIO", "").strip(),
                voto=row.get("VOTO", "").strip(),
                source_url=provenance.source_url,
                acquired_at=provenance.acquired_at,
                source_sha256=provenance.sha256,
            )
        )
    return records


def search_teor(records: Iterable[AcordaoRecord], query: str) -> list[AcordaoRecord]:
    """Case-insensitive literal search over authoritative text-bearing fields."""
    needle = query.casefold().strip()
    if not needle:
        return []
    return [
        record
        for record in records
        if needle
        in "\n".join(
            (
                record.assunto,
                record.sumario,
                record.acordao,
                record.decisao,
                record.relatorio,
                record.voto,
            )
        ).casefold()
    ]
