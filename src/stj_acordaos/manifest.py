"""STJ manifest — tracks download + IA upload state for each resource file."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

import structlog


log = structlog.get_logger()

HEADER = "arquivo,tipo,data_extracao,ia_status,n_registros,updated_at"


class ManifestSTJEntry:
    """A single STJ resource file with its sync state."""

    def __init__(
        self,
        arquivo: str,
        tipo: str,
        data_extracao: str = "",
        ia_status: str = "",
        n_registros: int = 0,
        updated_at: str = "",
    ) -> None:
        self.arquivo = arquivo
        self.tipo = tipo  # "zip" | "json"
        self.data_extracao = data_extracao
        self.ia_status = ia_status  # "" | "uploaded"
        self.n_registros = n_registros
        self.updated_at = updated_at


class ManifestSTJ:
    """Tracks download + IA upload state for STJ resource files.

    Persisted as ``stj-manifest.csv``.
    """

    def __init__(self, csv_path: Path) -> None:
        self._path = csv_path
        self._entries: dict[str, ManifestSTJEntry] = {}

    # ── Persistence ──────────────────────────────────────────────────────

    def load(self) -> int:
        """Load entries from the CSV file. Returns count of rows loaded."""
        if not self._path.exists():
            return 0
        count = 0
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("arquivo"):
                continue
            parts = line.split(",")
            if len(parts) < 6:  # noqa: PLR2004
                continue
            arquivo, tipo, data_extracao, ia_status, n_registros_str, updated_at = (
                parts[0], parts[1], parts[2], parts[3], parts[4], parts[5],
            )
            try:
                n_registros = int(n_registros_str)
            except ValueError:
                n_registros = 0
            self._entries[arquivo] = ManifestSTJEntry(
                arquivo=arquivo,
                tipo=tipo,
                data_extracao=data_extracao,
                ia_status=ia_status,
                n_registros=n_registros,
                updated_at=updated_at,
            )
            count += 1
        log.info("stj_manifest_loaded", path=str(self._path), count=count)
        return count

    def save(self) -> None:
        """Persist manifest to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = [HEADER]
        for e in sorted(self._entries.values(), key=lambda e: e.arquivo):
            lines.append(
                f"{e.arquivo},{e.tipo},{e.data_extracao},{e.ia_status},{e.n_registros},{e.updated_at}"
            )
        self._path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.info("stj_manifest_saved", path=str(self._path), entries=len(self._entries))

    # ── Mutation ─────────────────────────────────────────────────────────

    def upsert(
        self,
        arquivo: str,
        tipo: str,
        data_extracao: str,
        ia_status: str,
        n_registros: int,
    ) -> None:
        """Insert or update a manifest row."""
        now = datetime.now(UTC).isoformat(timespec="seconds")
        existing = self._entries.get(arquivo)
        if existing:
            existing.tipo = tipo
            existing.data_extracao = data_extracao
            existing.ia_status = ia_status
            existing.n_registros = n_registros
            existing.updated_at = now
        else:
            self._entries[arquivo] = ManifestSTJEntry(
                arquivo=arquivo,
                tipo=tipo,
                data_extracao=data_extracao,
                ia_status=ia_status,
                n_registros=n_registros,
                updated_at=now,
            )

    # ── Query ────────────────────────────────────────────────────────────

    def get_pending_uploads(self) -> list[ManifestSTJEntry]:
        """Return entries that have been downloaded but not yet uploaded to IA."""
        return [e for e in self._entries.values() if e.ia_status != "uploaded"]

    def to_df(self) -> list[dict]:
        """Return all entries as a list of dicts (for display/export)."""
        return [
            {
                "arquivo": e.arquivo,
                "tipo": e.tipo,
                "data_extracao": e.data_extracao,
                "ia_status": e.ia_status,
                "n_registros": e.n_registros,
                "updated_at": e.updated_at,
            }
            for e in sorted(self._entries.values(), key=lambda e: e.arquivo)
        ]

    def __len__(self) -> int:
        return len(self._entries)
