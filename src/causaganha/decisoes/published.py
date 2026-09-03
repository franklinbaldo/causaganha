"""Discover the published JURIS/STJ datasets that can back product queries.

The MCP search surface must not hardcode a growing list of years/months. TJRO
JURIS already publishes a canonical manifest; this module turns that authority
into deterministic public Parquet URLs. STJ currently publishes one canonical
Parquet and is represented explicitly as such.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from tjro_juris import archive as juris_archive
from tjro_juris.manifest import ManifestJuris


STJ_PARQUET_URL = "https://archive.org/download/stj-acordaos-primeira-secao/stj-acordaos.parquet"

TCU_PARQUET_URL = "https://archive.org/download/tcu-acordaos-2017-2026/tcu-acordaos.parquet"
"""Target public location for the TCU 2017-2026 TEOR artifact.

Materialization/publication is tracked separately (#1020); this constant fixes
the identity the search surface (#1011) is wired against.
"""

TCU_PUBLISH_EVIDENCE_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "data" / "tcu-acordaos-publish-proof.json"
)
"""Where scripts/tcu_acordaos_publish_teor.py (#1022) writes its read-back proof."""


@dataclass(frozen=True, slots=True)
class PublishedDecisionDataset:
    """One immutable public dataset usable for decision/content lookup."""

    fonte: str
    url: str
    periodo: str | None = None
    tipo: str | None = None
    registros: int | None = None


def _juris_remote_name(tipo: str, mes_ano: str) -> str:
    safe_tipo = tipo.replace(" ", "_").replace("/", "_")
    return f"{mes_ano}-{safe_tipo}.parquet"


def _juris_url(tipo: str, mes_ano: str) -> str:
    year = int(mes_ano[:4])
    remote_name = quote(_juris_remote_name(tipo, mes_ano))
    return f"https://archive.org/download/{juris_archive.IA_ITEM_PREFIX}-{year}/{remote_name}"


def discover_published_juris_datasets(manifest_text: str) -> list[PublishedDecisionDataset]:
    """Project the canonical JURIS manifest into public Parquet identities.

    Only entries whose manifest state is exactly ``uploaded`` and which report
    at least one document are returned. Pending/failed windows are not silently
    promoted into searchable coverage.
    """
    manifest = ManifestJuris.load_text(manifest_text, source=juris_archive.MANIFEST_DOWNLOAD_URL)
    datasets = [
        PublishedDecisionDataset(
            fonte="juris",
            url=_juris_url(entry.tipo, entry.mes_ano),
            periodo=entry.mes_ano,
            tipo=entry.tipo,
            registros=entry.n_docs,
        )
        for entry in manifest.all_entries()
        if entry.ia_status == "uploaded" and entry.n_docs > 0
    ]
    return sorted(datasets, key=lambda item: (item.periodo or "", item.tipo or "", item.url))


def discover_published_tcu_dataset(
    evidence_path: Path = TCU_PUBLISH_EVIDENCE_PATH,
) -> PublishedDecisionDataset | None:
    """Return the published TCU dataset, or ``None`` while publication is unproven.

    ``TCU_PARQUET_URL`` names the *target* location for the TCU 2017-2026
    artifact; by itself it is not evidence the artifact exists (#1025). This
    reads the read-back evidence ``scripts/tcu_acordaos_publish_teor.py``
    writes after independently re-downloading and re-verifying the artifact
    (#1022) — a missing file, invalid JSON, ``published: false``, or evidence
    for a different URL are all treated the same as "not published yet" so
    callers can never mistake a presumed target for a proven one.
    """
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if not isinstance(payload, dict) or payload.get("published") is not True:
        return None

    read_back = payload.get("read_back")
    if not isinstance(read_back, dict) or read_back.get("url") != TCU_PARQUET_URL:
        return None

    return PublishedDecisionDataset(fonte="tcu", url=TCU_PARQUET_URL, tipo="acordao")


def unpublished_fontes() -> frozenset[str]:
    """Fontes recognized by ``decisoes_buscar`` with no published dataset yet.

    This is the single authority for "recognized but not queryable" (#1036):
    MCP and site both derive it from the same discovery functions instead of
    each hand-maintaining a list of what is actually published. Only fontes
    whose status is knowable without a live fetch are represented — JURIS
    depends on the live manifest and is intentionally not summarized here.
    """
    fontes: set[str] = set()
    if discover_published_tcu_dataset() is None:
        fontes.add("tcu")
    return frozenset(fontes)


def discover_published_decision_datasets(manifest_text: str) -> list[PublishedDecisionDataset]:
    """Return the public datasets that currently support the TEOR product role."""
    return [
        *discover_published_juris_datasets(manifest_text),
        PublishedDecisionDataset(
            fonte="stj",
            url=STJ_PARQUET_URL,
            tipo="acordao",
        ),
    ]
