"""DataJud manifest — per-CNJ consultation state (incremental re-runs).

Persisted as ``datajud-manifest.csv`` with one row per (cnj, tribunal):
``cnj,tribunal,docs,consultado_em,status``. Re-runs consult only CNJs that
are missing, errored, or older than the freshness window.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


HEADER = "cnj,tribunal,docs,consultado_em,status"

STATUS_OK = "ok"
STATUS_ERRO = "erro"


class ManifestFormatError(ValueError):
    """The local manifest CSV is malformed (missing column, non-numeric docs, ...)."""


@dataclass
class ManifestDataJudEntry:
    """Consultation state of a single (cnj, tribunal) pair."""

    cnj: str
    tribunal: str
    docs: int = 0
    consultado_em: str = ""
    status: str = ""


class ManifestDataJud:
    """Tracks which CNJs were consulted, when, and how many docs came back."""

    def __init__(self) -> None:
        """Initialize an empty manifest."""
        self._entries: dict[tuple[str, str], ManifestDataJudEntry] = {}

    @staticmethod
    def _key(cnj: str, tribunal: str) -> tuple[str, str]:
        return (cnj, tribunal.lower())

    @classmethod
    def load_local(cls, path: Path) -> ManifestDataJud:
        """Load the manifest from a local CSV file (empty when missing).

        Raises `ManifestFormatError` on a malformed row (missing column,
        non-numeric `docs`) instead of leaking a bare `KeyError`/
        `ValueError` — callers get one nominal exception type to handle.
        """
        manifest = cls()
        if not path.exists():
            return manifest
        text = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                entry = ManifestDataJudEntry(
                    cnj=row["cnj"],
                    tribunal=row["tribunal"],
                    docs=int(row.get("docs", 0) or 0),
                    consultado_em=row.get("consultado_em", ""),
                    status=row.get("status", ""),
                )
            except (KeyError, ValueError) as exc:
                msg = f"malformed row in {path}: {exc}"
                raise ManifestFormatError(msg) from exc
            manifest._entries[cls._key(entry.cnj, entry.tribunal)] = entry
        return manifest

    def save_local(self, path: Path) -> None:
        """Persist the manifest to a local CSV file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            f"{e.cnj},{e.tribunal},{e.docs},{e.consultado_em},{e.status}"
            for e in sorted(self._entries.values(), key=lambda e: (e.tribunal, e.cnj))
        ]
        path.write_text("\n".join([HEADER, *rows]) + "\n", encoding="utf-8")

    def get(self, cnj: str, tribunal: str) -> ManifestDataJudEntry | None:
        """Return the entry for (cnj, tribunal), or None."""
        return self._entries.get(self._key(cnj, tribunal))

    def upsert(self, cnj: str, tribunal: str, *, docs: int, status: str) -> None:
        """Insert or update an entry, stamping ``consultado_em`` with now (UTC)."""
        now = datetime.now(UTC).isoformat(timespec="seconds")
        self._entries[self._key(cnj, tribunal)] = ManifestDataJudEntry(
            cnj=cnj,
            tribunal=tribunal.lower(),
            docs=docs,
            consultado_em=now,
            status=status,
        )

    def needs_refresh(self, cnj: str, tribunal: str, *, max_age_days: int) -> bool:
        """True when the CNJ was never consulted, errored, or is stale."""
        entry = self.get(cnj, tribunal)
        if entry is None or entry.status != STATUS_OK or not entry.consultado_em:
            return True
        try:
            consulted = datetime.fromisoformat(entry.consultado_em)
        except ValueError:
            return True
        if consulted.tzinfo is None:
            consulted = consulted.replace(tzinfo=UTC)
        return datetime.now(UTC) - consulted > timedelta(days=max_age_days)

    def all_entries(self) -> list[ManifestDataJudEntry]:
        """Return all entries."""
        return list(self._entries.values())

    def __len__(self) -> int:
        """Number of tracked (cnj, tribunal) pairs."""
        return len(self._entries)
