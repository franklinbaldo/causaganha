"""Config→result service layer for ``stj-acordaos``, free of Typer/echo (RFC 0013 Fase 2).

``__main__.py`` owns argv parsing and echoing results; this module owns the
actual work — discovering, downloading, deduping, uploading — so it can be
called from a future MCP tool or a different CLI framework without dragging
Typer along. Also drops ``ia_key``/``ia_secret`` as CLI options: Internet
Archive credentials are read from the environment only (``ia_credentials``),
never exposed as a parameter a schema (CLI or future MCP tool) could carry.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
import structlog

from stj_acordaos import archive as stj_archive
from stj_acordaos import client as stj_client
from stj_acordaos.client import STJWAFBlockedError
from stj_acordaos.dedup import dedup_acordaos
from stj_acordaos.manifest import ManifestSTJ


log = structlog.get_logger()

DEFAULT_DATA_DIR = Path("data/stj")
DEFAULT_MANIFEST = DEFAULT_DATA_DIR / "stj-manifest.csv"
DEFAULT_EXTRACT_DIR = DEFAULT_DATA_DIR / "extracted"
DEFAULT_PARQUET = DEFAULT_DATA_DIR / "stj-acordaos.parquet"


def ia_credentials() -> tuple[str, str]:
    """Read Internet Archive S3 credentials from the environment."""
    return os.environ.get("IA_ACCESS_KEY", ""), os.environ.get("IA_SECRET_KEY", "")


def _classify_resource(fmt: str, url: str) -> str | None:
    """Classify a CKAN resource as "zip" or "json"; None when neither.

    The STJ dataset carries auxiliary resources (e.g. a "dicionário de
    dados" CSV) that are not acórdãos data — downloading those as if they
    were JSON produces a file DuckDB's ``read_json`` chokes on later. Only
    resources explicitly declared zip/json (by CKAN ``format`` or URL
    suffix) are downloaded; anything else is skipped.
    """
    fmt = fmt.lower()
    url_lower = url.lower()
    if fmt == "zip" or url_lower.endswith(".zip"):
        return "zip"
    if fmt == "json" or url_lower.endswith(".json"):
        return "json"
    return None


def _already_uploaded(manifest: ManifestSTJ, dest_name: str, last_modified: str) -> bool:
    """True when *dest_name* is already on IA, unchanged since *last_modified*."""
    existing = manifest.get(dest_name)
    return (
        existing is not None
        and existing.ia_status == "uploaded"
        and existing.data_extracao == last_modified
    )


@dataclass
class DownloadOutcome:
    """Result of attempting to download+extract a single CKAN resource."""

    dest_name: str
    action: Literal[
        "skip_no_url",
        "skip_unrecognized_format",
        "skip_already_uploaded",
        "downloaded",
        "download_error",
        "extract_error",
    ]
    detail: str = ""
    n_extracted: int = 0


def download_one(
    resource: dict,
    manifest: ManifestSTJ,
    zip_dir: Path,
    extract_dir: Path,
) -> DownloadOutcome:
    """Download, extract and record a single CKAN resource.

    Raises ``STJWAFBlockedError`` upward unchanged (fail-fast: once the WAF
    has blocked this runner, every further request will fail too — the
    caller must not keep grinding through the remaining resources).
    """
    url: str = resource.get("url", "")
    name: str = resource.get("name", "") or resource.get("id", "unknown")
    fmt: str = (resource.get("format") or "").lower()
    last_modified: str = resource.get("last_modified") or resource.get("created") or ""

    if not url:
        return DownloadOutcome(dest_name=name, action="skip_no_url")

    tipo = _classify_resource(fmt, url)
    if tipo is None:
        return DownloadOutcome(dest_name=name, action="skip_unrecognized_format", detail=fmt)
    dest = zip_dir / f"{name}.{tipo}"

    if _already_uploaded(manifest, dest.name, last_modified):
        return DownloadOutcome(dest_name=name, action="skip_already_uploaded", detail=last_modified)

    log.info("stj_downloading", name=name, tipo=tipo)
    try:
        stj_client.download_resource(url, dest)
    except STJWAFBlockedError:
        raise
    except (httpx.HTTPError, OSError) as exc:
        return DownloadOutcome(dest_name=name, action="download_error", detail=str(exc))

    n_extracted = 0
    extract_error = ""
    if tipo == "zip":
        log.info("stj_extracting", file=dest.name)
        try:
            extracted = stj_client.extract_zip(dest, extract_dir)
            n_extracted = len(extracted)
        except (zipfile.BadZipFile, OSError) as exc:
            extract_error = str(exc)

    manifest.upsert(
        arquivo=dest.name,
        tipo=tipo,
        data_extracao=last_modified,
        ia_status="",
        n_registros=n_extracted,
    )
    manifest.save()

    if extract_error:
        return DownloadOutcome(
            dest_name=name, action="extract_error", detail=extract_error, n_extracted=n_extracted
        )
    return DownloadOutcome(dest_name=name, action="downloaded", n_extracted=n_extracted)


def restore_manifest_best_effort(manifest_path: Path) -> None:
    """Restore the manifest from IA when absent; never abort the run on failure.

    IA can return a transient error (observed: 503, not 404, for an item
    that has simply never been created yet) for reasons unrelated to whether
    a manifest actually exists. Failing to restore only costs redundant
    re-downloads of already-uploaded resources — no data is lost — so it
    must never abort the run.
    """
    if manifest_path.exists():
        return
    try:
        stj_archive.fetch_manifest(manifest_path)
    except httpx.HTTPError as exc:
        log.warning("stj_manifest_restore_failed", error=str(exc))


@dataclass
class UploadResult:
    """Result of ``upload_all``."""

    status: Literal["nothing_to_do", "no_data", "done"]
    ok: bool = True
    dedup_count: int | None = None


def upload_all(
    data_dir: Path,
    parquet_path: Path,
    manifest_path: Path,
    ia_key: str,
    ia_secret: str,
) -> UploadResult:
    """Dedup local JSONs into *parquet_path* and upload sources + parquet + manifest to IA."""
    manifest = ManifestSTJ(manifest_path)
    manifest.load()

    # Collect all JSON sources: extracted from ZIP + monthly downloads
    extract_dir = data_dir / "extracted"
    zip_dir = data_dir / "zips"
    json_files = sorted(
        list(extract_dir.glob("*.json") if extract_dir.exists() else [])
        + list(zip_dir.glob("*.json") if zip_dir.exists() else [])
    )
    dedup_count: int | None = None
    if json_files:
        log.info("stj_dedup_starting", count=len(json_files), parquet=str(parquet_path))
        dedup_count = dedup_acordaos(json_files, parquet_path)
        log.info("stj_dedup_done", records=dedup_count)
    elif not parquet_path.exists():
        # No local JSONs (every resource was already uploaded+unchanged and
        # `download` skipped it) and no local parquet (a blank runner never
        # restores it). If the manifest agrees nothing is pending, IA already
        # has the correct parquet from a prior run — there is genuinely
        # nothing to do, not an error.
        if manifest.get_pending_uploads():
            return UploadResult(status="no_data", ok=False)
        return UploadResult(status="nothing_to_do")

    # Upload original source files (ZIPs + monthly JSONs). Preserve the
    # entry's data_extracao/n_registros stamped by `download` — the download
    # skip compares data_extracao against CKAN's last_modified.
    all_sources = sorted(zip_dir.glob("*") if zip_dir.exists() else [])
    for src in all_sources:
        log.info("stj_uploading_source", file=src.name)
        ok = stj_archive.upload_parquet(src, ia_key, ia_secret)
        tipo_src = "zip" if src.suffix == ".zip" else "json"
        existing = manifest.get(src.name)
        manifest.upsert(
            arquivo=src.name,
            tipo=tipo_src,
            data_extracao=existing.data_extracao if existing else "",
            ia_status="uploaded" if ok else "",
            n_registros=existing.n_registros if existing else 0,
        )

    # Upload consolidated parquet
    log.info("stj_uploading_parquet", file=parquet_path.name)
    ok = stj_archive.upload_parquet(parquet_path, ia_key, ia_secret)

    manifest.upsert(
        arquivo=parquet_path.name,
        tipo="parquet",
        data_extracao="",
        ia_status="uploaded" if ok else "",
        n_registros=0,
    )
    manifest.save()

    # Push the manifest itself so a blank runner can restore it next run.
    log.info("stj_uploading_manifest", file=manifest_path.name)
    manifest_ok = stj_archive.upload_parquet(manifest_path, ia_key, ia_secret)
    if not manifest_ok:
        # Non-fatal: parquets are already on IA; the next run just re-uploads.
        log.warning("stj_manifest_upload_failed")

    return UploadResult(status="done", ok=ok, dedup_count=dedup_count)


@dataclass
class ManifestSummary:
    """Summary of the STJ manifest for the ``status`` command."""

    count: int
    uploaded: int
    rows: list[dict]

    @property
    def pending(self) -> int:
        """Entries not yet uploaded."""
        return self.count - self.uploaded


def manifest_summary(manifest_path: Path) -> ManifestSummary:
    """Load the manifest and summarize upload progress."""
    manifest = ManifestSTJ(manifest_path)
    count = manifest.load()
    rows = manifest.to_df() if count else []
    uploaded = sum(1 for r in rows if r["ia_status"] == "uploaded")
    return ManifestSummary(count=count, uploaded=uploaded, rows=rows)
