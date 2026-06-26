"""Manifest for TJRO JURIS crawl/upload state."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


HEADER = "tipo,mes_ano,ia_status,n_docs,updated_at"


@dataclass
class ManifestJurisEntry:
    """A single (tipo, mes_ano) pair with crawl/upload status."""

    tipo: str
    mes_ano: str
    ia_status: str = ""
    n_docs: int = 0
    updated_at: str = ""


class ManifestJuris:
    """Manifest tracking crawl and IA upload state for TJRO JURIS documents."""

    def __init__(self) -> None:
        """Initialize empty manifest."""
        self._entries: dict[tuple[str, str], ManifestJurisEntry] = {}

    @staticmethod
    def _key(tipo: str, mes_ano: str) -> tuple[str, str]:
        return (tipo, mes_ano)

    @classmethod
    def load_local(cls, path: Path) -> ManifestJuris:
        """Load manifest from a local CSV file."""
        m = cls()
        if not path.exists():
            return m
        text = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            entry = ManifestJurisEntry(
                tipo=row["tipo"],
                mes_ano=row["mes_ano"],
                ia_status=row.get("ia_status", ""),
                n_docs=int(row.get("n_docs", 0) or 0),
                updated_at=row.get("updated_at", ""),
            )
            m._entries[cls._key(entry.tipo, entry.mes_ano)] = entry
        return m

    def save_local(self, path: Path) -> None:
        """Save manifest to a local CSV file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            f"{e.tipo},{e.mes_ano},{e.ia_status},{e.n_docs},{e.updated_at}"
            for e in sorted(self._entries.values(), key=lambda e: (e.tipo, e.mes_ano))
        ]
        lines = [HEADER, *rows]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def get(self, tipo: str, mes_ano: str) -> ManifestJurisEntry | None:
        """Return entry for (tipo, mes_ano) or None."""
        return self._entries.get(self._key(tipo, mes_ano))

    def upsert(self, entry: ManifestJurisEntry) -> None:
        """Insert or update an entry, stamping updated_at."""
        entry.updated_at = datetime.now(UTC).isoformat(timespec="seconds")
        self._entries[self._key(entry.tipo, entry.mes_ano)] = entry

    def all_entries(self) -> list[ManifestJurisEntry]:
        """Return all entries."""
        return list(self._entries.values())

    def pending_upload(self) -> list[ManifestJurisEntry]:
        """Return entries where ia_status != 'uploaded'."""
        return [e for e in self._entries.values() if e.ia_status != "uploaded"]
