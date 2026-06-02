#!/usr/bin/env python3

SATURDAY_WEEKDAY = 5
MIN_ITEM_ID_PARTS = 4
HTTP_200_OK = 200

"""Consolidate DJEN ZIP files into daily Parquet files.

This script downloads all ZIP files for a specific date from Internet Archive,
converts them to consolidated Parquet files (one per table type, all tribunals),
and uploads them back to IA.

Usage:
    # Consolidate specific date
    python scripts/pipeline/consolidate.py --date 2026-01-27

    # Dry run (don't upload)
    python scripts/pipeline/consolidate.py --date 2026-01-27 --dry-run
"""

import argparse
import asyncio
import decimal
import json
import os
import shutil
import tempfile
import threading
import time
import traceback
import unicodedata
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


# Disable strict decimal traps that cause crashes in ibis/sqlglot
# See: https://github.com/ibis-project/ibis/issues/9638 (similar)
# This is required because sqlglot may attempt to convert "binary_double_nan"
# which triggers InvalidOperation if traps are enabled.
decimal.getcontext().traps[decimal.InvalidOperation] = False

import contextlib
import sys

import duckdb
import httpx
import ibis
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from causaganha.config import TRIBUNAIS
from causaganha.consolidate.consolidation_manifest import (
    collect_table_stats,
    update_consolidation_manifest,
)
from causaganha.consolidate.ndjson_validator import validate_ndjson_sample
from causaganha.consolidate.schema_registry import CURRENT_VERSION, kv_metadata_sql_fragment
from causaganha.consolidate.validation import validate_parquet
from causaganha.storage.connection import get_connection
from causaganha.storage.djen_schema import (
    FIELD_CODIGO_CLASSE,
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_NOME_CLASSE,
    FIELD_NOME_ORGAO,
    FIELD_NUMERO_COMUNICACAO,
    FIELD_NUMERO_OAB,
    FIELD_NUMERO_PROCESSO,
    FIELD_TIPO_COMUNICACAO,
    FIELD_TIPO_DOCUMENTO,
    FIELD_UF_OAB,
)
from scripts.pipeline.ia_s3 import (
    CircuitBreaker,
    create_upload_client,
    get_ia_item_id,
    get_ia_s3_auth,
    parse_deadline,
    upload_to_ia,
)


@dataclass
class ConsolidationContext:
    """Mutable caches for a single consolidation run.

    Encapsulates module-level mutable state so that:
    - Tests can create isolated contexts without side effects.
    - Multiple runs in the same process don't leak cache entries.
    - The signature matches the immutable-config style of ``run.py``.
    """

    # Cache for tribunal stopped checks (tribunal -> date -> bool)
    tribunal_stopped_cache: dict[str, dict[str, bool]] = dataclass_field(default_factory=dict)

    # Cache for consolidation candidates (list of dates)
    consolidation_candidates: list[str] | None = None


# Checkpoint state file path
_CHECKPOINT_STATE_FILE = Path("data/consolidate-checkpoint.json")

# Sync manifest path (written by djen-backup/engine.py)
_SYNC_MANIFEST_FILE = Path("data/sync-manifest.csv")


def load_sync_manifest(path: Path = _SYNC_MANIFEST_FILE) -> dict[str, list[dict[str, Any]]]:
    """Load sync-manifest.csv into a by-date lookup.

    The sync-manifest is the canonical state written by djen-backup/engine.py.
    Using it as an intermediate source avoids the slow IA metadata API fallback
    in list_zips_for_date() when manifest.parquet has not yet been regenerated.

    Returns:
        Dict mapping date_str → list of entries with keys:
        ``tribunal``, ``item_id``, ``filename``, ``absent``.
        Includes BOTH uploaded (ia_status=uploaded) and confirmed-absent
        (djen_status=absent) entries so that present_count in list_zips_for_date()
        correctly mirrors the manifest.parquet behaviour (which counts .absent files
        as "present" for the completeness check).
        Empty dict if file does not exist.
    """
    if not path.exists():
        logger.info("sync_manifest_not_found", path=str(path))
        return {}

    by_date: dict[str, list[dict[str, Any]]] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("tribunal"):
                continue
            parts = stripped_line.split(",")
            if len(parts) < 3:
                continue
            tribunal = parts[0].upper()
            date_str = parts[1]
            ia_status = parts[2]
            djen_status = parts[3] if len(parts) > 3 else ""

            if ia_status == "uploaded":
                year = date_str[:4]
                item_id = f"djen-{tribunal.lower()}-{year}"
                filename = f"djen-{date_str}-{tribunal}.zip"
                by_date.setdefault(date_str, []).append(
                    {
                        "tribunal": tribunal,
                        "item_id": item_id,
                        "filename": filename,
                        "absent": False,
                    }
                )
            elif djen_status == "absent":
                # Tribunal confirmed no publication on this date — counts as "present"
                # for the completeness check but produces no ZIP to download.
                by_date.setdefault(date_str, []).append(
                    {"tribunal": tribunal, "item_id": "", "filename": "", "absent": True}
                )
    except Exception as e:
        logger.warning("sync_manifest_load_failed", path=str(path), error=str(e))
        return {}

    total_zips = sum(1 for v in by_date.values() for e in v if not e["absent"])
    total_absent = sum(1 for v in by_date.values() for e in v if e["absent"])
    logger.info(
        "sync_manifest_loaded", dates=len(by_date), total_zips=total_zips, total_absent=total_absent
    )
    return by_date


def load_checkpoint_state() -> dict[str, Any]:
    """Load checkpoint state from disk.

    Returns:
        dict with keys:
            - current_date: date being processed (str | None)
            - processed_zips: list of ZIP filenames already processed
            - completed_dates: list of fully completed dates
    """
    if not _CHECKPOINT_STATE_FILE.exists():
        return {
            "current_date": None,
            "processed_zips": [],
            "completed_dates": [],
        }

    try:
        with _CHECKPOINT_STATE_FILE.open("r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("checkpoint_load_failed", error=str(e))
        return {
            "current_date": None,
            "processed_zips": [],
            "completed_dates": [],
        }


def save_checkpoint_state(state: dict[str, Any]) -> None:
    """Save checkpoint state to disk."""
    _CHECKPOINT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _CHECKPOINT_STATE_FILE.open("w") as f:
            json.dump(state, f, indent=2)
        logger.info(
            "checkpoint_saved",
            date=state.get("current_date"),
            processed=len(state.get("processed_zips", [])),
        )
    except Exception as e:
        logger.exception("checkpoint_save_failed", error=str(e))


def update_checkpoint_progress(date: str, zip_filename: str) -> None:
    """Update checkpoint state after processing a ZIP."""
    state = load_checkpoint_state()

    # If switching to a new date, reset processed_zips
    if state["current_date"] != date:
        state["current_date"] = date
        state["processed_zips"] = []

    # Add ZIP to processed list
    if zip_filename not in state["processed_zips"]:
        state["processed_zips"].append(zip_filename)

    save_checkpoint_state(state)


def mark_date_complete(date: str) -> None:
    """Mark a date as fully consolidated."""
    state = load_checkpoint_state()

    if date not in state["completed_dates"]:
        state["completed_dates"].append(date)

    # Reset current_date and processed_zips
    state["current_date"] = None
    state["processed_zips"] = []

    save_checkpoint_state(state)
    logger.info("date_marked_complete", date=date)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
)
def _download_manifest_file(url: str, output_path: Path) -> None:
    """Download manifest file with retries."""
    with httpx.Client() as client:
        resp = client.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)


def fetch_manifest_records() -> list[dict]:
    """Download and return all manifest records from Internet Archive.

    Returns empty list on error.
    """
    manifest_url = "https://archive.org/download/causaganha-catalog/manifest.parquet"
    logger.info("fetching_manifest", url=manifest_url)

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        # Download manifest with retry
        try:
            _download_manifest_file(manifest_url, tmp_path)
        except Exception as e:
            logger.warning("manifest_download_failed", error=str(e))
            return []

        # Query using DuckDB to get records
        con = duckdb.connect()
        try:
            # Fetch all records
            df = con.execute(f"SELECT * FROM read_parquet('{tmp_path}')").df()
            records = df.to_dict("records")
        except Exception:
            logger.warning("manifest_invalid_parquet")
            records = []
        finally:
            con.close()
            with contextlib.suppress(Exception):
                tmp_path.unlink()

    except Exception as e:
        logger.warning("fetch_manifest_failed", error=str(e))
        return []
    else:
        return records


def fetch_consolidation_candidates(
    manifest: list[dict] | None = None,
    sync_manifest: dict[str, list[dict[str, Any]]] | None = None,
) -> list[str]:
    """Fetch dates needing consolidation.

    Priority order:
      1. manifest.parquet (in-memory or downloaded from IA) — authoritative,
         knows exactly which dates have ZIPs and which already have Parquets.
      2. sync-manifest.csv (local file) — fast fallback: dates with uploaded
         ZIPs that are not yet in the consolidation checkpoint.
    Returns dates sorted descending (newest first).
    """
    # 1a. In-memory manifest (already fetched)
    if manifest is not None:
        logger.info("fetching_consolidation_candidates_from_memory", records=len(manifest))
        try:
            df_data = [{"date": m["date"], "file_type": m["file_type"]} for m in manifest]
            t = ibis.memtable(df_data, columns=["date", "file_type"])
            agg = t.group_by("date").agg(
                has_zip=(t["file_type"] == "zip").sum(),
                has_parquet=(t["file_type"] == "parquet").sum(),
            )
            result = (
                agg.filter((agg["has_zip"] > 0) & (agg["has_parquet"] == 0))
                .order_by(agg["date"].desc())
                .select("date")
                .execute()["date"]
                .tolist()
            )
            return [str(d) for d in result]
        except Exception as e:
            logger.warning("fetch_candidates_failed_memory", error=str(e))
            return []

    # 1b. Download manifest.parquet from IA and query it
    manifest_url = "https://archive.org/download/causaganha-catalog/manifest.parquet"
    logger.info("fetching_consolidation_candidates_from_url", url=manifest_url)
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
        query = """
            SELECT date
            FROM read_parquet('https://archive.org/download/causaganha-catalog/manifest.parquet')
            GROUP BY date
            HAVING SUM(CASE WHEN file_type='zip' THEN 1 ELSE 0 END) > 0
               AND SUM(CASE WHEN file_type='parquet' THEN 1 ELSE 0 END) = 0
            ORDER BY date DESC
        """
        result = con.execute(query).fetchall()
        candidates = [str(r[0]) for r in result]
        if candidates:
            logger.info("candidates_from_manifest_parquet", count=len(candidates))
            return candidates
    except Exception as e:
        logger.warning("fetch_candidates_from_manifest_parquet_failed", error=str(e))
    finally:
        con.close()

    # 2. Fallback: sync-manifest.csv — dates uploaded but not yet consolidated
    if sync_manifest:
        checkpoint = load_checkpoint_state()
        completed = set(checkpoint.get("completed_dates", []))
        candidates = sorted(
            (d for d in sync_manifest if d not in completed),
            reverse=True,
        )
        logger.info(
            "candidates_from_sync_manifest",
            total_dates=len(sync_manifest),
            completed=len(completed),
            candidates=len(candidates),
        )
        return candidates

    return []


class CheckpointManager:
    """Manages local checkpoint state for backfill progress."""

    def __init__(self, filepath: Path) -> None:
        """Initialize with checkpoint file path."""
        self.filepath = filepath

    def load(self) -> str | None:
        """Load the last checked date from checkpoint file."""
        if not self.filepath.exists():
            return None
        try:
            with self.filepath.open("r") as f:
                data = json.load(f)
                return data.get("last_checked")
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, date_str: str) -> None:
        """Save the last checked date to checkpoint file."""
        try:
            with self.filepath.open("w") as f:
                json.dump({"last_checked": date_str}, f)
        except OSError as e:
            logger.warning("checkpoint_save_failed", error=str(e))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Ibis scalar UDFs — the only Python called per-row during SQL execution.
# ---------------------------------------------------------------------------
@ibis.udf.scalar.python
def djen_uuid5(s: str) -> str:
    """Deterministic UUIDv5 in the CausaGanha DJEN namespace."""
    if s is None:
        return None  # type: ignore[return-value]
    return str(uuid.uuid5(NAMESPACE_DJEN, s))


@ibis.udf.scalar.python
def normalize_name(s: str) -> str:
    """Strip accents, uppercase, collapse whitespace."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


# Table types to consolidate - Defined below via TABLE_SCHEMAS


def list_local_zips(directory: str) -> tuple[list[dict[str, Any]], int]:
    """Find all ZIP files in a local directory."""
    logger.info("listing_local_zips", directory=directory)
    zips: list[dict[str, Any]] = []
    local_dir = Path(directory)

    if not local_dir.exists():
        logger.warning("local_zips_not_found", directory=directory)
        return zips, 0

    for zip_file in local_dir.glob("*.zip"):
        # Extract tribunal from filename: djen-2026-01-23-TJSP.zip
        parts = zip_file.stem.split("-")
        tribunal = parts[-1] if len(parts) >= MIN_ITEM_ID_PARTS else "UNKNOWN"
        zips.append(
            {
                "filename": zip_file.name,
                "tribunal": tribunal,
                "item_id": "local-test",
                "size": zip_file.stat().st_size,
                "local_path": str(zip_file),
            },
        )

    return zips, len(zips)


def list_zips_for_date(
    date: str,
    manifest: list[dict] | None = None,
    sync_manifest: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Find all ZIP files for a specific date on IA.

    Priority order (fastest → slowest):
      1. manifest.parquet records (in-memory, already fetched)
      2. sync-manifest.csv records (local file, O(1) lookup)
      3. IA metadata API per tribunal (slow — 40+ HTTP calls, avoid)
    """
    logger.info("listing_zips", date=date)
    zips: list[dict[str, Any]] = []

    # 1. manifest.parquet (fast, already in memory)
    if manifest:
        files = [m for m in manifest if m["date"] == date]
        present = set()
        for f in files:
            if f["file_type"] in ("zip", "absent"):
                present.add(f["tribunal"])
                if f["file_type"] == "zip":
                    zips.append(
                        {
                            "filename": f["file_name"],
                            "tribunal": f["tribunal"],
                            "item_id": f["ia_item"],
                            "size": 0,
                        }
                    )
        return zips, len(present)

    # 2. sync-manifest.csv (fast, avoids per-tribunal IA API calls)
    if sync_manifest is not None:
        entries = sync_manifest.get(date, [])
        present_count = len(entries)  # includes both uploaded ZIPs and confirmed-absent
        zips.extend(
            {
                "filename": e["filename"],
                "tribunal": e["tribunal"],
                "item_id": e["item_id"],
                "size": 0,
            }
            for e in entries
            if not e["absent"]
        )
        logger.info("zips_from_sync_manifest", date=date, zips=len(zips), present=present_count)
        return zips, present_count

    # 3. IA metadata API per tribunal (slow fallback — only used if both sources absent)
    present = set()
    for tribunal in TRIBUNAIS:
        item_id = get_ia_item_id(tribunal, date)
        try:
            url = f"https://archive.org/metadata/{item_id}"
            response = httpx.get(url, timeout=30)
            if response.status_code == HTTP_200_OK:
                data = response.json()
                files = data.get("files", [])

                target_zip = f"djen-{date}-{tribunal.upper()}.zip"
                target_absent = f"djen-{date}-{tribunal.upper()}.absent"

                for file_info in files:
                    filename = file_info.get("name", "")
                    if filename == target_zip:
                        present.add(tribunal)
                        zips.append(
                            {
                                "filename": filename,
                                "tribunal": tribunal,
                                "item_id": item_id,
                                "size": file_info.get("size", 0),
                            }
                        )
                    elif filename == target_absent:
                        present.add(tribunal)

        except Exception as e:
            logger.warning("metadata_fetch_failed", item_id=item_id, error=str(e))

    logger.info("zips_found_via_api", count=len(zips), date=date)
    return zips, len(present)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True,
)
def download_zip(item_id: str, filename: str, output_path: Path) -> bool:
    """Download ZIP from Internet Archive using httpx with retries.

    Raises Exception on failure (after retries exhausted).
    """
    url = f"https://archive.org/download/{item_id}/{filename}"
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
        response.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
    return output_path.exists() and output_path.stat().st_size > 0


def extract_json_from_zip(zip_path: Path) -> list[dict[str, Any]]:
    """Extract and parse JSON data from ZIP file."""
    records: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    try:
                        content = zf.read(name).decode("utf-8")
                        data = json.loads(content)
                        if isinstance(data, list):
                            records.extend(data)
                        elif isinstance(data, dict):
                            # Handle wrapped items or direct communication
                            if "items" in data and isinstance(data["items"], list):
                                records.extend(data["items"])
                            else:
                                records.append(data)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
    except zipfile.BadZipFile:
        logger.warning("bad_zip_file", path=str(zip_path))
    return records


# ---------------------------------------------------------------------------
# Ibis helpers — small composable building blocks for the table builders.
# ---------------------------------------------------------------------------


def _safe(col: ibis.Column) -> ibis.Column:
    """Cast to string, strip whitespace, fill NULL with ''."""
    return col.cast("string").strip().fill_null("")


def _col(t: ibis.Table, *names: str) -> ibis.Column:
    """COALESCE the first existing columns by *names*, or literal(None).

    Casts all columns to string before coalescing to avoid type precedence errors
    when mixing date and string columns.
    """
    existing = [t[n].cast("string") for n in names if n in t.columns]
    if not existing:
        return ibis.literal(None)
    return ibis.coalesce(*existing) if len(existing) > 1 else existing[0]


def _struct_field(struct_col: ibis.Column, *names: str) -> ibis.Column:
    """Safely access first existing field from a struct (handles naming variants)."""
    field_names = struct_col.type().names
    for name in names:
        if name in field_names:
            return struct_col[name]
    return ibis.literal(None)


def _date_expr(raw: ibis.Table) -> ibis.Column:
    """Parse the availability date from either naming convention."""
    return _safe(_col(raw, *FIELD_DATA_DISPONIBILIZACAO)).left(10).try_cast("date")


def _com_id(raw: ibis.Table) -> ibis.Column:
    """Communication UUID: hash of DJEN original id + tribunal."""
    return djen_uuid5(_safe(raw.id) + ":" + raw.src_tribunal)


def _texto_id(raw: ibis.Table) -> ibis.Column:
    """Text UUID: content-addressed hash of the text itself."""
    txt = _safe(raw.texto)
    return ibis.cases((txt != "", djen_uuid5(txt)), else_="")


def _parte_id(d: ibis.Column) -> ibis.Column:
    """Party UUID: hash of normalized name."""
    return djen_uuid5(normalize_name(d["nome"].cast("string").fill_null("")))


def _adv_global_id(da: ibis.Column, tribunal: ibis.Column) -> ibis.Column:
    """Advogado UUID: prefer OAB+UF key, fall back to nome+tribunal+orig_id."""
    adv = da["advogado"]
    oab = _safe(_struct_field(adv, *FIELD_NUMERO_OAB))
    uf = _safe(_struct_field(adv, *FIELD_UF_OAB))
    nome = _safe(adv["nome"])
    orig_id = _safe(
        ibis.coalesce(
            _struct_field(adv, "id"),
            _struct_field(da, "advogado_id"),
        ),
    )
    return ibis.cases(
        ((oab != "") & (uf != ""), djen_uuid5(oab + ":" + uf)),
        else_=djen_uuid5(nome + ":" + tribunal + ":" + orig_id),
    )


def _partitions(raw: ibis.Table, item_id: str) -> dict[str, ibis.Expr]:
    """Common partitioning columns shared across most tables."""
    d = _date_expr(raw)
    return {
        "p_ano": d.year().fill_null(0).cast("int32"),
        "p_mes": d.month().fill_null(0).cast("int32"),
        "p_item_ia": ibis.literal(item_id),
    }


# ---------------------------------------------------------------------------
# Table builders — each returns an Ibis expression that SELECT-s into its
# target table.  No raw SQL.  UUIDs computed via the djen_uuid5() UDF,
# name normalization via normalize_name() UDF, flattening via .unnest().
# ---------------------------------------------------------------------------


def _build_comunicacoes(raw: ibis.Table, item_id: str) -> ibis.Table:
    return raw.select(
        id=_com_id(raw),
        original_id=_safe(raw.id),
        tribunal=raw.src_tribunal,
        numero_processo=_safe(_col(raw, *FIELD_NUMERO_PROCESSO)),
        numero_processo_mascara=_safe(_col(raw, "numeroprocessocommascara")),
        data_disponibilizacao=_date_expr(raw),
        tipo_comunicacao=_safe(_col(raw, *FIELD_TIPO_COMUNICACAO)),
        nome_orgao=_safe(_col(raw, *FIELD_NOME_ORGAO)),
        meio=_safe(_col(raw, "meio")),
        link=_safe(_col(raw, "link")),
        tipo_documento=_safe(_col(raw, *FIELD_TIPO_DOCUMENTO)),
        nome_classe=_safe(_col(raw, *FIELD_NOME_CLASSE)),
        codigo_classe=_safe(_col(raw, *FIELD_CODIGO_CLASSE)),
        numero_comunicacao=_safe(_col(raw, *FIELD_NUMERO_COMUNICACAO)),
        hash=_safe(_col(raw, "hash")),
        processed_at=ibis.now(),
        texto_id=_texto_id(raw),
        **_partitions(raw, item_id),
    )


def _build_textos(raw: ibis.Table, _item_id: str) -> ibis.Table:
    txt = _safe(raw.texto)
    return (
        raw.filter(txt != "")
        .select(
            id=djen_uuid5(txt),
            texto=txt,
        )
        .distinct()
    )


def _build_destinatarios(raw: ibis.Table, item_id: str) -> ibis.Table:
    t = raw.select(
        com_key=_safe(raw.id) + ":" + raw.src_tribunal,
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        src_item_id=ibis.literal(item_id),
        d=raw.destinatarios.unnest(),
    )
    return t.select(
        comunicacao_id=djen_uuid5(t.com_key),
        tribunal=t.src_tribunal,
        nome=_safe(t.d["nome"]),
        polo=_safe(t.d["polo"]),
        parte_id=_parte_id(t.d),
        p_ano=t.disp_date.year().fill_null(0).cast("int32"),
        p_mes=t.disp_date.month().fill_null(0).cast("int32"),
        p_item_ia=t.src_item_id,
    )


def _build_partes(raw: ibis.Table, _item_id: str) -> ibis.Table:
    t = raw.select(d=raw.destinatarios.unnest())
    nome_norm = normalize_name(t.d["nome"].cast("string").fill_null(""))
    return (
        t.filter(nome_norm != "")
        .select(
            id=djen_uuid5(nome_norm),
            nome_normalizado=nome_norm,
            nome_original=_safe(t.d["nome"]),
        )
        .distinct(on="id")
    )


def _build_comunicacao_advogados(raw: ibis.Table, _item_id: str) -> ibis.Table:
    t = raw.select(
        com_key=_safe(raw.id) + ":" + raw.src_tribunal,
        src_tribunal=raw.src_tribunal,
        da=raw.destinatarioadvogados.unnest(),
    )
    return t.select(
        comunicacao_id=djen_uuid5(t.com_key),
        tribunal=t.src_tribunal,
        advogado_id=_adv_global_id(t.da, t.src_tribunal),
    )


def _build_advogados(raw: ibis.Table, item_id: str) -> ibis.Table:
    t = raw.select(
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        src_item_id=ibis.literal(item_id),
        da=raw.destinatarioadvogados.unnest(),
    )
    adv = t.da["advogado"]
    return t.filter(adv.notnull()).select(
        id=_adv_global_id(t.da, t.src_tribunal),
        original_id=_safe(
            ibis.coalesce(_struct_field(adv, "id"), _struct_field(t.da, "advogado_id")),
        ),
        tribunal=t.src_tribunal,
        nome=_safe(adv["nome"]),
        numero_oab=_safe(_struct_field(adv, *FIELD_NUMERO_OAB)),
        uf_oab=_safe(_struct_field(adv, *FIELD_UF_OAB)),
        p_ano=t.disp_date.year().fill_null(0).cast("int32"),
        p_mes=t.disp_date.month().fill_null(0).cast("int32"),
        p_item_ia=t.src_item_id,
    )


def _build_advogado_nomes(raw: ibis.Table, _item_id: str) -> ibis.Table:
    t = raw.select(
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        da=raw.destinatarioadvogados.unnest(),
    )
    adv = t.da["advogado"]
    return t.filter(adv.notnull()).select(
        advogado_id=_adv_global_id(t.da, t.src_tribunal),
        nome=_safe(adv["nome"]),
        tribunal=t.src_tribunal,
        first_seen=t.disp_date,
    )


def _build_representacoes(raw: ibis.Table, item_id: str) -> ibis.Table:
    # Cross-join: unnest destinatarios, then unnest destinatarioadvogados
    step1 = raw.select(
        com_key=_safe(raw.id) + ":" + raw.src_tribunal,
        src_tribunal=raw.src_tribunal,
        disp_date=_date_expr(raw),
        src_item_id=ibis.literal(item_id),
        d=raw.destinatarios.unnest(),
        destinatarioadvogados=raw.destinatarioadvogados,
    )
    step2 = step1.select(
        step1.com_key,
        step1.src_tribunal,
        step1.disp_date,
        step1.src_item_id,
        step1.d,
        da=step1.destinatarioadvogados.unnest(),
    )
    adv = step2.da["advogado"]
    return step2.filter(adv.notnull()).select(
        comunicacao_id=djen_uuid5(step2.com_key),
        tribunal=step2.src_tribunal,
        advogado_id=_adv_global_id(step2.da, step2.src_tribunal),
        parte_id=_parte_id(step2.d),
        polo=_safe(step2.d["polo"]),
        p_ano=step2.disp_date.year().fill_null(0).cast("int32"),
        p_mes=step2.disp_date.month().fill_null(0).cast("int32"),
        p_item_ia=step2.src_item_id,
    )


def _build_processos(raw: ibis.Table, item_id: str) -> ibis.Table:
    return raw.select(
        numero_processo=_safe(_col(raw, *FIELD_NUMERO_PROCESSO)),
        tribunal=raw.src_tribunal,
        data=_date_expr(raw),
        comunicacao_id=_com_id(raw),
        **_partitions(raw, item_id),
    )


def _build_classificacoes(raw: ibis.Table, _item_id: str) -> ibis.Table:
    """Build classificacoes table — keyword-based outcome classification.

    Uses text patterns to classify judicial communications into outcome
    categories (procedente, improcedente, parcialmente procedente, etc.).
    This provides a baseline; LLM-based analysis can refine later.
    """
    txt = _safe(raw.texto)
    txt_lower = txt.lower()
    texto_id = djen_uuid5(txt)

    # Only classify non-empty texts
    has_text = txt != ""

    # Keyword-based outcome detection
    # Order matters: check "parcialmente procedente" before "procedente"
    outcome = ibis.cases(
        (txt_lower.contains("parcialmente procedente"), "PARTIAL"),
        (txt_lower.contains("improcedente"), "LOSS"),
        (txt_lower.contains("procedente"), "WIN"),
        (txt_lower.contains("acordo") | txt_lower.contains("transação"), "SETTLEMENT"),
        else_="UNKNOWN",
    )

    # Decision type detection
    decision_type = ibis.cases(
        (txt_lower.contains("acórdão") | txt_lower.contains("acordão"), "acórdão"),
        (txt_lower.contains("sentença"), "sentença"),
        (txt_lower.contains("decisão interlocutória"), "decisão interlocutória"),
        else_="outro",
    )

    # Low confidence for keyword-based classification
    confidence = ibis.literal(0.3).cast("float64")

    return (
        raw.filter(has_text)
        .filter(outcome != "UNKNOWN")
        .select(
            texto_id=texto_id,
            metodo=ibis.literal("keyword_v1"),
            outcome=outcome,
            decision_type=decision_type,
            winner_advogado_id=ibis.null().cast("string"),
            loser_advogado_id=ibis.null().cast("string"),
            confidence=confidence,
            classified_at=ibis.now(),
        )
        .distinct(on=["texto_id"])
    )


# Ordered list: tables with FK dependencies come after their parents.
_TABLE_BUILDERS: tuple[tuple[str, Any], ...] = (
    ("comunicacoes", _build_comunicacoes),
    ("textos", _build_textos),
    ("destinatarios", _build_destinatarios),
    ("partes", _build_partes),
    ("comunicacao_advogados", _build_comunicacao_advogados),
    ("advogados", _build_advogados),
    ("advogado_nomes", _build_advogado_nomes),
    ("representacoes", _build_representacoes),
    ("processos", _build_processos),
    ("classificacoes", _build_classificacoes),
)


def _load_and_transform(
    con: ibis.BaseBackend,
    ndjson_dir: Path,
    item_id: str,
) -> dict[str, int]:
    """Load raw per-tribunal NDJSON into DuckDB, produce all 10 tables via Ibis.

    The only raw SQL is ``read_json_auto`` (DuckDB-specific loader).  Everything
    else — UUIDs, name normalization, unnesting, deduplication — is expressed
    as Ibis table expressions executed by the DuckDB backend.
    """
    # One raw SQL call: read_json_auto with filename for tribunal derivation.
    con.raw_sql(
        f"CREATE OR REPLACE TABLE _staging AS "
        f"SELECT * FROM read_json_auto('{ndjson_dir}/*.ndjson', "
        f"filename=true, union_by_name=true)",
    )
    staging = con.table("_staging")

    # Derive _tribunal from filename and add item_id — pure Ibis, no Python loop.
    raw_expr = staging.mutate(
        src_tribunal=staging.filename.split("/")[-1].split("__")[0],
        src_item_id=ibis.literal(item_id),
    )
    con.create_table("raw_records", raw_expr, overwrite=True)
    raw = con.table("raw_records")

    counts: dict[str, int] = {}
    for table_name, builder in _TABLE_BUILDERS:
        expr = builder(raw, item_id)
        con.insert(table_name, expr)
        row_count = con.table(table_name).count().execute()
        counts[table_name] = row_count
        if row_count:
            logger.info("table_populated", table=table_name, rows=row_count)

    # Clean up staging tables
    con.drop_table("raw_records", force=True)
    con.drop_table("_staging", force=True)
    return counts


# Explicit Schema Definitions using Ibis
TABLE_SCHEMAS = {
    "comunicacoes": ibis.schema(
        {
            "id": "string",
            "original_id": "string",
            "tribunal": "string",
            "numero_processo": "string",
            "numero_processo_mascara": "string",
            "data_disponibilizacao": "date",
            "tipo_comunicacao": "string",
            "nome_orgao": "string",
            "meio": "string",
            "link": "string",
            "tipo_documento": "string",
            "nome_classe": "string",
            "codigo_classe": "string",
            "numero_comunicacao": "string",
            "hash": "string",
            "processed_at": "timestamp",
            "texto_id": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "advogados": ibis.schema(
        {
            "id": "string",
            "original_id": "string",
            "tribunal": "string",
            "nome": "string",
            "numero_oab": "string",
            "uf_oab": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "advogado_nomes": ibis.schema(
        {
            "advogado_id": "string",
            "nome": "string",
            "tribunal": "string",
            "first_seen": "date",
        },
    ),
    "destinatarios": ibis.schema(
        {
            "comunicacao_id": "string",
            "tribunal": "string",
            "nome": "string",
            "polo": "string",
            "parte_id": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    "comunicacao_advogados": ibis.schema(
        {
            "comunicacao_id": "string",
            "tribunal": "string",
            "advogado_id": "string",
        },
    ),
    "textos": ibis.schema(
        {
            "id": "string",
            "texto": "string",
        },
    ),
    "representacoes": ibis.schema(
        {
            "comunicacao_id": "string",
            "tribunal": "string",
            "advogado_id": "string",
            "parte_id": "string",
            "polo": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    # Process activity index: one row per communication event, NOT a dimension table.
    # For a true process dimension (first/last seen, court unit), build a materialized view.
    "processos": ibis.schema(
        {
            "numero_processo": "string",
            "tribunal": "string",
            "data": "date",
            "comunicacao_id": "string",
            "p_ano": "int32",
            "p_mes": "int32",
            "p_item_ia": "string",
        },
    ),
    # Outcome classification per unique text, decoupled from comunicacoes.
    # Composite key: (texto_id, metodo)
    "classificacoes": ibis.schema(
        {
            "texto_id": "string",
            "metodo": "string",
            "outcome": "string",
            "decision_type": "string",
            "winner_advogado_id": "string",
            "loser_advogado_id": "string",
            "confidence": "float64",
            "classified_at": "timestamp",
        },
    ),
    # Party dimension table with normalized keys for entity resolution.
    "partes": ibis.schema(
        {
            "id": "string",
            "nome_normalizado": "string",
            "nome_original": "string",
        },
    ),
}
TABLES = list(TABLE_SCHEMAS.keys())


def init_tables(con: ibis.BaseBackend) -> None:
    """Initialize tables with correct schema using Ibis."""
    for table, schema in TABLE_SCHEMAS.items():
        con.create_table(table, schema=schema, overwrite=True)


_CONSOLIDATION_META_OVERRIDES = {
    "x-archive-meta-title": "DJEN Consolidated - {date_str}",
    "x-archive-meta-description": (
        "Consolidated Parquet files from Brazilian court communications."
    ),
}


async def _upload_consolidated(
    client: httpx.AsyncClient,
    item_id: str,
    file_path: Path,
    date_str: str,
    circuit_breaker: CircuitBreaker | None = None,
) -> bool:
    """Upload consolidated file to IA with consolidation-specific metadata."""
    overrides = {k: v.format(date_str=date_str) for k, v in _CONSOLIDATION_META_OVERRIDES.items()}
    return await upload_to_ia(
        client,
        item_id,
        file_path,
        date_str,
        metadata_overrides=overrides,
        circuit_breaker=circuit_breaker,
    )


async def _upload_marker(client: httpx.AsyncClient, item_id: str, date_str: str) -> bool:
    """Upload consolidation marker to Internet Archive.

    Creates empty _consolidated.marker file to signal that this date
    has been successfully consolidated and should not be reprocessed.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_consolidated.marker", delete=False
        ) as f:
            marker_path = Path(f.name)
            # Empty file - existence is the signal

        logger.info("uploading_marker", item_id=item_id)
        success = await _upload_consolidated(client, item_id, marker_path, date_str)

        # Cleanup temp file
        with contextlib.suppress(Exception):
            marker_path.unlink()

    except Exception as e:
        logger.exception("marker_upload_failed", item_id=item_id, error=str(e))
        return False
    else:
        return success


def _is_tribunal_stopped(
    tribunal: str,
    target_date: date,
    manifest: list[dict] | None = None,
    absent_threshold: int = 60,
    ctx: ConsolidationContext | None = None,
) -> bool:
    """Check if a tribunal has been absent for 60+ consecutive days before target_date.

    If manifest is provided, use it to check (fast).
    Otherwise, scans the last N days backward from target_date using IA metadata API (slow).
    """
    if ctx is None:
        ctx = ConsolidationContext()
    date_str = target_date.strftime("%Y-%m-%d")

    # Check cache
    if tribunal in ctx.tribunal_stopped_cache:
        if date_str in ctx.tribunal_stopped_cache[tribunal]:
            return ctx.tribunal_stopped_cache[tribunal][date_str]
    else:
        ctx.tribunal_stopped_cache[tribunal] = {}

    # 1. Manifest-based check (fast)
    if manifest:
        # Build lookup for this tribunal if not in cache
        # Note: We use a simple lookup for speed
        trib_key = f"_lookup_{tribunal}"
        if trib_key not in ctx.tribunal_stopped_cache:
            ctx.tribunal_stopped_cache[trib_key] = {}
            for m in manifest:
                if m["tribunal"] == tribunal:
                    d = m["date"]
                    if d not in ctx.tribunal_stopped_cache[trib_key]:
                        ctx.tribunal_stopped_cache[trib_key][d] = []
                    ctx.tribunal_stopped_cache[trib_key][d].append(m["file_type"])

        tribunal_files = ctx.tribunal_stopped_cache[trib_key]

        for days_back in range(1, absent_threshold + 1):
            check_date = target_date - timedelta(days=days_back)
            if check_date.weekday() >= SATURDAY_WEEKDAY:  # skip weekends
                continue

            check_date_str = check_date.strftime("%Y-%m-%d")

            # If date not in manifest at all, can't conclude stopped
            if check_date_str not in tribunal_files:
                result = False
                ctx.tribunal_stopped_cache[tribunal][date_str] = result
                return result

            # If we find a .zip (not just .absent), tribunal is active
            if "zip" in tribunal_files[check_date_str]:
                result = False
                ctx.tribunal_stopped_cache[tribunal][date_str] = result
                return result

            # If neither zip nor absent, can't conclude stopped
            if "absent" not in tribunal_files[check_date_str]:
                result = False
                ctx.tribunal_stopped_cache[tribunal][date_str] = result
                return result

        result = True
        ctx.tribunal_stopped_cache[tribunal][date_str] = result
        return result

    # 2. IA Metadata API-based check (slow fallback)
    logger.info("is_tribunal_stopped_api_fallback", tribunal=tribunal, date=date_str)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    def _check_tribunal_api(url: str) -> dict:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    for days_back in range(1, absent_threshold + 1):
        check_date = target_date - timedelta(days=days_back)
        if check_date.weekday() >= SATURDAY_WEEKDAY:  # skip weekends
            continue

        check_date_str = check_date.strftime("%Y-%m-%d")
        item_id = get_ia_item_id(tribunal, check_date_str)
        url = f"https://archive.org/metadata/{item_id}"

        try:
            data = _check_tribunal_api(url)
            files = data.get("files", [])
            target_zip = f"djen-{check_date_str}-{tribunal.upper()}.zip"
            target_absent = f"djen-{check_date_str}-{tribunal.upper()}.absent"

            tribunal_found = False

            for f in files:
                if not isinstance(f, dict):
                    continue
                name = f.get("name", "")

                if name == target_zip:
                    result = False
                    ctx.tribunal_stopped_cache[tribunal][date_str] = result
                    return result
                if name == target_absent:
                    tribunal_found = True
                    break

            # If no file for this tribunal on this day, can't conclude stopped
            if not tribunal_found:
                result = False
                ctx.tribunal_stopped_cache[tribunal][date_str] = result
                return result

        except Exception:
            # On error, assume not stopped (conservative)
            result = False
            ctx.tribunal_stopped_cache[tribunal][date_str] = result
            return result

    # All checked days had .absent marker - tribunal is stopped
    result = True
    ctx.tribunal_stopped_cache[tribunal][date_str] = result
    return result


def _needs_consolidation(
    date_str: str,
    manifest: list[dict] | None = None,
    *,
    must_be_complete: bool = False,
    ctx: ConsolidationContext | None = None,
) -> bool:
    """Check whether *date_str* has collected ZIPs but no consolidated parquets or marker on IA.

    If *must_be_complete* is True, also verifies that all expected tribunals are present,
    EXCEPT tribunals that have been consistently absent for 60+ days (stopped tribunals).
    """
    # 1. Use manifest if available (fast)
    if manifest:
        files = [m for m in manifest if m["date"] == date_str]
        if not files:
            return False

        has_zips = any(f["file_type"] in ("zip", "absent") for f in files)
        has_consolidated = any(
            f["file_type"] == "parquet" or "_consolidated" in f.get("file_name", "") for f in files
        )

        if not (has_zips and not has_consolidated):
            return False

        if must_be_complete:
            present_tribunais = {
                f["tribunal"] for f in files if f["file_type"] in ("zip", "absent")
            }
            target_d = date.fromisoformat(date_str)

            for trib in TRIBUNAIS:
                if trib not in present_tribunais and not _is_tribunal_stopped(
                    trib, target_d, manifest, ctx=ctx
                ):
                    return False
            return True

        return True

    # 2. IA metadata API fallback
    item_id = f"djen-{date_str}"
    url = f"https://archive.org/metadata/{item_id}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    def _check_date_api(url: str) -> dict:
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    try:
        data = _check_date_api(url)
        files = data.get("files", [])
        has_zips = False
        has_consolidated = False
        present_tribunais = set()

        for f in files:
            if not isinstance(f, dict):
                continue
            name = f.get("name", "")
            # Check for ZIPs or absent markers as proof of attempted collection
            if name.endswith((".zip", ".absent")):
                has_zips = True
                # Identify tribunal from filename
                parts = name.replace(".zip", "").replace(".absent", "").split("-")
                if len(parts) >= MIN_ITEM_ID_PARTS:
                    present_tribunais.add(parts[-1])

            # Check for any .parquet file or the sentinel marker as proof of consolidation
            if name.endswith(".parquet") or name == "_consolidated.marker":
                has_consolidated = True

        if not (has_zips and not has_consolidated):
            return False

        if must_be_complete:
            target_d = date.fromisoformat(date_str)
            active_tribunals = []
            present_tribunais = set()

            # Slow fallback: fetch individually
            for trib in TRIBUNAIS:
                if not _is_tribunal_stopped(trib, target_d, ctx=ctx):
                    active_tribunals.append(trib)
                    item_id = get_ia_item_id(trib, date_str)
                    url = f"https://archive.org/metadata/{item_id}"
                    try:
                        data = _check_date_api(url)
                        files = data.get("files", [])
                        target_zip = f"djen-{date_str}-{trib.upper()}.zip"
                        target_absent = f"djen-{date_str}-{trib.upper()}.absent"

                        has_zip = False

                        for f in files:
                            name = f.get("name", "")
                            if name in (target_zip, target_absent):
                                has_zip = True

                        if has_zip:
                            present_tribunais.add(trib)
                    except Exception:
                        pass  # missing

            # Must have data for all active (non-stopped) tribunals
            missing_active = [t for t in active_tribunals if t not in present_tribunais]
            if missing_active:
                logger.debug(
                    "date_incomplete",
                    date=date_str,
                    missing_count=len(missing_active),
                    missing=missing_active[:5],  # log first 5
                )
                return False

        result = True
    except Exception:
        return False
    else:
        return result


def _all_tribunals_stopped(
    target_date: date,
    manifest: list[dict] | None = None,
    ctx: ConsolidationContext | None = None,
) -> bool:
    """Check if ALL tribunals are stopped (60+ days absent) at target_date.

    This is the natural stopping condition for backfill - when there's no more
    historical data from any tribunal.
    """
    return all(
        _is_tribunal_stopped(tribunal, target_date, manifest, ctx=ctx) for tribunal in TRIBUNAIS
    )


def find_next_unconsolidated(
    manifest: list[dict] | None = None,
    checkpoint_file: Path | None = None,
    ctx: ConsolidationContext | None = None,
    sync_manifest: dict[str, list[dict[str, Any]]] | None = None,
) -> str | None:
    """Find the most recent date needing consolidation.

    First tries to fetch candidates from the catalog manifest (fast).
    Falls back to sync-manifest.csv, then to walking backward from today (slow).

    Returns the date string or None if everything is consolidated.
    """
    if ctx is None:
        ctx = ConsolidationContext()

    # 1. Try manifest-based discovery (fast, minimal API calls)
    if ctx.consolidation_candidates is None:
        ctx.consolidation_candidates = fetch_consolidation_candidates(manifest, sync_manifest)

    if ctx.consolidation_candidates:
        while ctx.consolidation_candidates:
            candidate = ctx.consolidation_candidates.pop(0)
            # We found a candidate from manifest. It definitely has ZIPs and no parquets.
            # We return it directly. consolidate_date will verify completeness.
            logger.info("candidate_from_manifest", date=candidate)
            return candidate

    # 2. Fallback: Walk backward from today (slow, heavy API usage)
    if checkpoint_file is None:
        checkpoint_file = Path(".backfill_checkpoint.json")

    checkpoint = CheckpointManager(checkpoint_file)
    last_checked = checkpoint.load()

    today = datetime.now(UTC).date()
    days_ago = 0

    if last_checked:
        try:
            last_date = date.fromisoformat(last_checked)
            delta = (today - last_date).days
            if delta >= 0:
                days_ago = delta
                logger.info("resuming_from_checkpoint", date=last_checked, days_ago=days_ago)
        except ValueError:
            pass

    max_iterations = 1000  # Safety limit (roughly 3 years of weekdays)
    floor_date = date(2020, 1, 1)  # Don't scan pre-2020 dates (no useful data)

    while days_ago < max_iterations:
        d = today - timedelta(days=days_ago)
        if d < floor_date:
            logger.info("backfill_floor_reached", floor=str(floor_date))
            return None
        d_str = d.strftime("%Y-%m-%d")

        # Skip weekends
        if d.weekday() >= SATURDAY_WEEKDAY:
            days_ago += 1
            continue

        # Check if we've gone back far enough (all tribunals stopped)
        if _all_tribunals_stopped(d, manifest, ctx=ctx):
            logger.info(
                "backfill_complete", date=d_str, days_ago=days_ago, reason="all_tribunals_stopped"
            )
            return None

        # Backfill requires completeness — only consolidate when everything is gathered
        if _needs_consolidation(d_str, manifest, must_be_complete=True, ctx=ctx):
            logger.info("unconsolidated_date_found", date=d_str, days_ago=days_ago)
            checkpoint.save(d_str)
            return d_str

        checkpoint.save(d_str)
        days_ago += 1

    # Safety limit reached
    logger.warning("backfill_max_iterations", max_iterations=max_iterations)
    return None


_duckdb_export_lock = threading.Lock()


def _export_table_sync(
    table_name: str,
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str = "",
) -> tuple[Path, float, int] | None:
    """Export a single table to Parquet (blocking DuckDB work).

    Returns (output_path, size_mb, row_count) or None when table is empty.
    Intended to be called via asyncio.to_thread so it doesn't block the loop.
    """
    with _duckdb_export_lock:
        t = con.table(table_name)
        count = t.count().execute()
        if count == 0:
            return None
        output_path = output_dir / f"{table_name}.parquet"
        kv_clause = kv_metadata_sql_fragment(item_id) if item_id else ""
        copy_opts = "FORMAT PARQUET, COMPRESSION ZSTD"
        if kv_clause:
            copy_opts = f"{copy_opts}, {kv_clause}"
        con.raw_sql(
            f"COPY {table_name} TO '{output_path}' ({copy_opts})",
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        return output_path, size_mb, int(count)


async def _export_and_upload_table(
    table_name: str,
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str,
    client: httpx.AsyncClient,
    date_str: str,
    *,
    dry_run: bool,
    circuit_breaker: CircuitBreaker | None = None,
) -> tuple[bool, float, int]:
    """Export single table to Parquet and upload. Returns (success, size_mb, uploaded_count).

    The blocking DuckDB export runs in a thread via asyncio.to_thread so that
    asyncio.gather can run multiple table exports truly in parallel (same
    behaviour as the previous ThreadPoolExecutor path).
    """
    try:
        export_result = await asyncio.to_thread(
            _export_table_sync, table_name, con, output_dir, item_id
        )
        if export_result is None:
            return False, 0.0, 0

        output_path, size_mb, count = export_result
        logger.info(
            "parquet_created",
            table=table_name,
            rows=count,
            size_mb=f"{size_mb:.1f}",
        )

        vr = await asyncio.to_thread(validate_parquet, output_path, table_name)
        if not vr.passed:
            logger.error("validation_blocked_upload", table=table_name, errors=vr.errors)
            return False, size_mb, 0
        if vr.warnings:
            logger.warning("validation_warnings", table=table_name, warnings=vr.warnings)

        # Upload if not dry run
        uploaded = 0
        if not dry_run and await _upload_consolidated(
            client,
            item_id,
            output_path,
            date_str,
            circuit_breaker=circuit_breaker,
        ):
            uploaded = 1
            logger.info("uploaded", table=table_name)

        result = (True, size_mb, uploaded)
    except Exception as e:
        logger.exception("parquet_export_failed", table=table_name, error=str(e))
        return False, 0.0, 0
    else:
        return result


def process_zip_entry(
    zip_entry: dict[str, Any],
    tmp_path: Path,
    ndjson_dir: Path,
    item_id: str,
    local_zips: str | None,
) -> tuple[int, int]:
    """Process a single ZIP entry.

    Returns: (success_count, records_count)
    """
    filename = str(zip_entry["filename"])
    tribunal = str(zip_entry["tribunal"])

    logger.info(
        "processing_zip_start",
        filename=filename,
        tribunal=tribunal,
    )

    zip_path = tmp_path / filename

    # Download or copy
    if local_zips and "local_path" in zip_entry:
        try:
            shutil.copy2(zip_entry["local_path"], zip_path)
        except Exception as e:
            logger.warning("local_copy_failed", filename=filename, error=str(e))
            return 0, 0
    else:
        # Prefer per-entry item_id (canonical tribunal-year item) when provided.
        download_item = str(zip_entry.get("item_id") or item_id)
        if not download_zip(download_item, filename, zip_path):
            logger.warning("download_failed", filename=filename)
            return 0, 0

    # Extract
    records = extract_json_from_zip(zip_path)
    if not records:
        logger.warning("no_records_found", filename=filename)
        with contextlib.suppress(Exception):
            zip_path.unlink()
        return 0, 0

    # Write to NDJSON (per-ZIP file, no lock)
    # Use unique filename to avoid collision: {tribunal}__{zip_stem}.ndjson
    zip_stem = Path(filename).stem
    ndjson_filename = f"{tribunal}__{zip_stem}.ndjson"
    ndjson_path = ndjson_dir / ndjson_filename

    try:
        with ndjson_path.open("w") as f:
            for rec in records:
                if isinstance(rec, dict):
                    f.write(json.dumps(rec, default=str) + "\n")
    except Exception as e:
        logger.exception("ndjson_write_failed", file=ndjson_filename, error=str(e))
        return 0, 0

    with contextlib.suppress(Exception):
        zip_path.unlink()

    return 1, len(records)


def list_zips_for_tribunal_year(
    tribunal: str,
    year: int,
    sync_manifest: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Find all uploaded ZIPs for (tribunal, year) from sync-manifest.

    Each returned entry has: filename, tribunal, item_id, date, size (0).
    """
    tribunal_upper = tribunal.upper()
    year_prefix = f"{year:04d}-"
    zips: list[dict[str, Any]] = []

    for date_str, entries in sync_manifest.items():
        if not date_str.startswith(year_prefix):
            continue
        for entry in entries:
            if entry["absent"]:
                continue
            if entry["tribunal"] != tribunal_upper:
                continue
            zips.append(
                {
                    "filename": entry["filename"],
                    "tribunal": tribunal_upper,
                    "item_id": entry["item_id"],
                    "date": date_str,
                    "size": 0,
                },
            )

    zips.sort(key=lambda z: z["date"])
    logger.info(
        "zips_for_tribunal_year",
        tribunal=tribunal_upper,
        year=year,
        zips=len(zips),
    )
    return zips


def check_tribunal_year_consolidated(item_id: str) -> bool:
    """Check if a tribunal-year item already has the consolidation marker."""
    url = f"https://archive.org/metadata/{item_id}"
    try:
        with httpx.Client() as client:
            resp = client.get(url, timeout=30, follow_redirects=True)
            if resp.status_code != HTTP_200_OK:
                return False
            files = resp.json().get("files", [])
            return any(f.get("name") == "_consolidated.marker" for f in files)
    except httpx.HTTPError:
        return False


def consolidate_tribunal_year(
    tribunal: str,
    year: int,
    sync_manifest: dict[str, list[dict[str, Any]]],
    *,
    dry_run: bool = False,
    local_zips: str | None = None,
    max_zips: int = 0,
    workers: int = 16,
) -> dict[str, int | float]:
    """Consolidate all ZIPs for a (tribunal, year) pair into Parquet files.

    Output parquets are uploaded to the canonical per-tribunal-year item
    ``djen-{tribunal_lower}-{year}``, alongside the raw ZIPs.
    """
    stats: dict[str, int | float] = {
        "zips_processed": 0,
        "records": 0,
        "parquets_created": 0,
        "uploaded": 0,
        "uploaded_mb": 0.0,
    }
    tribunal_upper = tribunal.upper()
    item_id = f"djen-{tribunal_upper.lower()}-{year}"
    date_tag = f"{year}-01-01"  # metadata date stamp for upload headers

    if local_zips:
        zips, _ = list_local_zips(local_zips)
        zips = [z for z in zips if z["tribunal"].upper() == tribunal_upper]
        logger.info(
            "using_local_zips",
            directory=local_zips,
            count=len(zips),
            tribunal=tribunal_upper,
        )
    else:
        zips = list_zips_for_tribunal_year(tribunal_upper, year, sync_manifest)

    if max_zips > 0 and len(zips) > max_zips:
        logger.info("limiting_zips", total=len(zips), max_zips=max_zips)
        zips = zips[:max_zips]

    if not zips:
        logger.info("nothing_to_consolidate", tribunal=tribunal_upper, year=year)
        return stats

    con = get_connection(":memory:")
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ndjson_dir = tmp_path / "ndjson"
        ndjson_dir.mkdir()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    process_zip_entry,
                    zip_entry,
                    tmp_path,
                    ndjson_dir,
                    item_id,
                    local_zips,
                ): zip_entry
                for zip_entry in zips
            }
            for future in as_completed(futures):
                zip_entry = futures[future]
                try:
                    success_cnt, records_cnt = future.result()
                    stats["zips_processed"] += success_cnt
                    stats["records"] += records_cnt
                except Exception as e:
                    logger.exception(
                        "zip_processing_error",
                        zip=zip_entry["filename"],
                        error=str(e),
                    )

        non_empty_tables: set[str] = set()
        if stats["records"] > 0:
            table_counts = _load_and_transform(con, ndjson_dir, item_id)
            non_empty_tables = {name for name, cnt in table_counts.items() if int(cnt or 0) > 0}
            logger.info("transform_complete", tables=table_counts)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        logger.info("exporting_parquets", table_count=len(TABLES), item=item_id)

        ia_auth = get_ia_s3_auth()
        if not ia_auth and not dry_run:
            logger.warning(
                "ia_credentials_not_found",
                hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY or run `ia configure`",
            )

        ia_circuit_breaker = CircuitBreaker(threshold=5)
        export_failures = 0

        async def _run_upload_phase() -> None:
            nonlocal export_failures
            async with create_upload_client(ia_auth or "") as client:
                results = []
                for table_name in TABLES:
                    try:
                        res = await _export_and_upload_table(
                            table_name,
                            con,
                            output_dir,
                            item_id,
                            client,
                            date_tag,
                            dry_run=dry_run,
                            circuit_breaker=ia_circuit_breaker,
                        )
                        results.append(res)
                    except Exception as exc:
                        results.append(exc)
                for table_name, result in zip(TABLES, results, strict=True):
                    if isinstance(result, Exception):
                        logger.exception(
                            "table_export_error",
                            table=table_name,
                            error=str(result),
                        )
                        if table_name in non_empty_tables:
                            export_failures += 1
                        continue
                    success, size_mb, uploaded = result
                    if success:
                        stats["parquets_created"] += 1
                        stats["uploaded"] += uploaded
                        stats["uploaded_mb"] += size_mb
                    elif table_name in non_empty_tables:
                        export_failures += 1

                expected = len(non_empty_tables)
                if (
                    stats["parquets_created"] == expected
                    and export_failures == 0
                    and stats["parquets_created"] > 0
                    and not dry_run
                ):
                    if await _upload_marker(client, item_id, date_tag):
                        logger.info("marker_uploaded", item_id=item_id)
                    else:
                        logger.warning("marker_upload_failed", item_id=item_id)
                elif stats["parquets_created"] > 0 and (
                    stats["parquets_created"] != expected or export_failures > 0
                ):
                    logger.error(
                        "marker_blocked_by_incomplete_exports",
                        item_id=item_id,
                        expected_parquets=expected,
                        parquets_created=stats["parquets_created"],
                        export_failures=export_failures,
                    )

        asyncio.run(_run_upload_phase())

    return stats


def consolidate_date(
    date: str,
    manifest: list[dict] | None = None,
    *,
    sync_manifest: dict[str, list[dict[str, Any]]] | None = None,
    dry_run: bool = False,
    force: bool = False,
    local_zips: str | None = None,
    max_zips: int = 0,
    workers: int = 16,
) -> dict[str, int | float]:
    """Consolidate all tribunals for a date into single Parquet files.

    Args:
        date: Date string in YYYY-MM-DD format.
        manifest: In-memory manifest.parquet records (fastest source).
        sync_manifest: In-memory sync-manifest.csv records (fast fallback).
        dry_run: If True, skip uploading to Internet Archive.
        force: If True, consolidate even if the day is incomplete.
        local_zips: Local directory containing ZIPs (for testing).
        max_zips: Maximum ZIPs to process (0 = unlimited).
        workers: Number of parallel workers for processing ZIPs.
    """
    stats = {
        "zips_processed": 0,
        "records": 0,
        "parquets_created": 0,
        "uploaded": 0,
        "uploaded_mb": 0.0,
    }
    item_id = f"djen-{date}"

    # Load checkpoint state
    checkpoint = load_checkpoint_state()
    processed_zips_set = set(checkpoint.get("processed_zips", []))

    if checkpoint.get("current_date") == date and processed_zips_set:
        logger.info(
            "resuming_from_checkpoint", date=date, already_processed=len(processed_zips_set)
        )

    # Find all ZIPs and check if day's matrix is complete
    if local_zips:
        zips, present_count = list_local_zips(local_zips)
        logger.info("using_local_zips", directory=local_zips, count=len(zips))
    else:
        zips, present_count = list_zips_for_date(date, manifest, sync_manifest)

    # Filter out already processed ZIPs
    original_count = len(zips)
    zips = [z for z in zips if z["filename"] not in processed_zips_set]

    if original_count > len(zips):
        logger.info(
            "skipping_processed_zips",
            total=original_count,
            remaining=len(zips),
            skipped=original_count - len(zips),
        )

    # Limit ZIPs if max_zips specified (for backfill batching)
    if max_zips > 0 and len(zips) > max_zips:
        logger.info("limiting_zips", total=len(zips), max_zips=max_zips)
        zips = zips[:max_zips]

    expected_count = len(TRIBUNAIS)
    if not force and present_count < expected_count:
        logger.warning(
            "day_not_complete_skipping",
            date=date,
            present=present_count,
            expected=expected_count,
            missing=expected_count - present_count,
        )
        return stats

    if not zips:
        # All ZIPs processed, mark date complete
        if original_count > 0 and not dry_run:
            mark_date_complete(date)
        logger.info("nothing_to_consolidate", date=date)
        return stats

    # Use Ibis with DuckDB backend (singleton to prevent conflicts)
    con = get_connection(":memory:")
    init_tables(con)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ndjson_dir = tmp_path / "ndjson"
        ndjson_dir.mkdir()

        # Phase 1: Extract ZIPs → raw per-tribunal NDJSON (zero Python mutation)
        # Parallel processing of ZIPs with checkpoint after each
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    process_zip_entry,
                    zip_entry,
                    tmp_path,
                    ndjson_dir,
                    item_id,
                    local_zips,
                ): zip_entry
                for zip_entry in zips
            }

            for future in as_completed(futures):
                zip_entry = futures[future]
                zip_filename = zip_entry["filename"]
                try:
                    success_cnt, records_cnt = future.result()
                    stats["zips_processed"] += success_cnt
                    stats["records"] += records_cnt

                    # Save checkpoint after each ZIP
                    if success_cnt > 0 and not dry_run:
                        update_checkpoint_progress(date, zip_filename)

                except Exception as e:
                    logger.exception("zip_processing_error", zip=zip_filename, error=str(e))

        # Phase 2: Ibis-driven transformation (UDFs, unnest, distinct)
        non_empty_tables: set[str] = set()
        if stats["records"] > 0:
            ndjson_vr = validate_ndjson_sample(ndjson_dir)
            if not ndjson_vr.passed:
                logger.error(
                    "ndjson_validation_blocked",
                    errors=ndjson_vr.errors,
                    item_id=item_id,
                )
                return stats
            if ndjson_vr.warnings:
                logger.warning("ndjson_validation_warnings", warnings=ndjson_vr.warnings)
            table_counts = _load_and_transform(con, ndjson_dir, item_id)
            non_empty_tables = {name for name, cnt in table_counts.items() if int(cnt or 0) > 0}
            logger.info("transform_complete", tables=table_counts)

        # Phase 3: Export to Parquet and upload (parallel for 2-3x speedup)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        logger.info("exporting_parquets", table_count=len(TABLES))

        # Resolve IA S3 credentials for upload client
        ia_auth = get_ia_s3_auth()
        if not ia_auth and not dry_run:
            logger.warning(
                "ia_credentials_not_found",
                hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY or run `ia configure`",
            )

        ia_circuit_breaker = CircuitBreaker(threshold=5)
        uploaded_tables: list[str] = []
        export_failures = 0

        async def _run_upload_phase() -> None:
            """Phase 3+4: sequential Parquet export/upload then marker upload."""
            nonlocal export_failures
            async with create_upload_client(ia_auth or "") as client:
                results = []
                for table_name in TABLES:
                    try:
                        res = await _export_and_upload_table(
                            table_name,
                            con,
                            output_dir,
                            item_id,
                            client,
                            date,
                            dry_run=dry_run,
                            circuit_breaker=ia_circuit_breaker,
                        )
                        results.append(res)
                    except Exception as exc:
                        results.append(exc)
                for table_name, result in zip(TABLES, results, strict=True):
                    if isinstance(result, Exception):
                        logger.exception("table_export_error", table=table_name, error=str(result))
                        if table_name in non_empty_tables:
                            export_failures += 1
                    else:
                        success, size_mb, uploaded = result
                        if success:
                            stats["parquets_created"] += 1
                            stats["uploaded"] += uploaded
                            stats["uploaded_mb"] += size_mb
                            if uploaded:
                                uploaded_tables.append(table_name)
                        elif table_name in non_empty_tables:
                            export_failures += 1

                # Phase 4: Upload consolidation marker only when ALL non-empty
                # tables produced valid Parquets (no partial uploads).
                expected = len(non_empty_tables)
                if (
                    stats["parquets_created"] == expected
                    and export_failures == 0
                    and stats["parquets_created"] > 0
                    and not dry_run
                ):
                    if await _upload_marker(client, item_id, date):
                        logger.info("marker_uploaded", item_id=item_id)
                        mark_date_complete(date)
                    else:
                        logger.warning("marker_upload_failed", item_id=item_id)
                elif stats["parquets_created"] > 0 and (
                    stats["parquets_created"] != expected or export_failures > 0
                ):
                    logger.error(
                        "marker_blocked_by_incomplete_exports",
                        item_id=item_id,
                        expected_parquets=expected,
                        parquets_created=stats["parquets_created"],
                        export_failures=export_failures,
                    )

        asyncio.run(_run_upload_phase())

        # Phase 5: Update consolidation manifest — only for tables that reached IA,
        # and only on real runs (not dry-run).
        if uploaded_tables and not dry_run:
            try:
                table_stats = collect_table_stats(output_dir, uploaded_tables)
                update_consolidation_manifest(
                    item_id=item_id,
                    date_str=date,
                    schema_version=CURRENT_VERSION,
                    table_stats=table_stats,
                )
            except OSError as exc:
                logger.warning("manifest_update_failed", error=str(exc))

    return stats


def _print_stats(stats: dict[str, int]) -> None:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate DJEN ZIPs to daily Parquets")
    parser.add_argument("--date", help="Date to consolidate (YYYY-MM-DD)")
    parser.add_argument(
        "--tribunal",
        help="Tribunal code (e.g. TJRO). Requires --year. "
        "Consolidates all ZIPs for that (tribunal, year) into the IA item djen-{tribunal}-{year}.",
    )
    parser.add_argument("--year", type=int, help="Year for --tribunal mode (e.g. 2026)")
    parser.add_argument("--dry-run", action="store_true", help="Don't upload to IA")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Consolidate even if day is not complete",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Find the most recent unconsolidated date and process it (auto-stops per tribunal)",
    )
    parser.add_argument(
        "--max-zips",
        type=int,
        default=0,
        help="Maximum ZIPs to process per run (0 = unlimited, for backfill)",
    )
    parser.add_argument(
        "--local-zips",
        help="Use local ZIPs from directory instead of downloading from IA (for testing)",
    )
    parser.add_argument(
        "--deadline",
        help="Exit after this duration (e.g., 10m, 600s)",
        default="10m",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,  # Reduced from 16 to align with collect.py gradual scaling and reduce OOM risk
        help="Number of parallel workers for processing ZIPs",
    )
    args = parser.parse_args()

    deadline_sec = parse_deadline(args.deadline)
    start_time = time.time()

    total_stats = {
        "zips_processed": 0,
        "records": 0,
        "parquets_created": 0,
        "uploaded": 0,
        "uploaded_mb": 0.0,
    }

    # Load sync-manifest.csv (written by djen-backup, available after download-state step)
    # Used as fallback when manifest.parquet is unavailable or stale.
    sync_manifest = load_sync_manifest()

    # Fetch manifest.parquet once if in backfill mode or scanning needed
    manifest = None
    if args.backfill or not args.date:
        manifest = fetch_manifest_records()

    if args.tribunal or args.year:
        if not (args.tribunal and args.year):
            logger.error("tribunal_year_requires_both", tribunal=args.tribunal, year=args.year)
            return 2
        try:
            stats = consolidate_tribunal_year(
                args.tribunal,
                args.year,
                sync_manifest,
                dry_run=args.dry_run,
                local_zips=args.local_zips,
                max_zips=args.max_zips,
                workers=args.workers,
            )
            _print_stats(stats)
            for k in total_stats:
                total_stats[k] += stats.get(k, 0)
        except Exception as e:
            logger.exception("consolidation_aborted", error=str(e))
            traceback.print_exc()
            return 1

    elif args.date:
        # Explicit date — existing behaviour
        try:
            stats = consolidate_date(
                args.date,
                manifest,
                sync_manifest=sync_manifest,
                dry_run=args.dry_run,
                force=args.force,
                local_zips=args.local_zips,
                max_zips=args.max_zips,
                workers=args.workers,
            )
            _print_stats(stats)
            for k in total_stats:
                total_stats[k] += stats.get(k, 0)
        except Exception as e:
            logger.exception("consolidation_aborted", error=str(e))
            traceback.print_exc()
            return 1

    elif args.backfill:
        # Backfill: process multiple unconsolidated dates until deadline
        dates_processed = 0
        ctx = ConsolidationContext()

        while True:
            # Check deadline - leave 120s margin for upload completion
            if deadline_sec > 0:
                elapsed = time.time() - start_time
                if elapsed > deadline_sec - 120:
                    break

            target_date_or_none = find_next_unconsolidated(
                manifest, ctx=ctx, sync_manifest=sync_manifest
            )
            if target_date_or_none is None:
                break

            target_date = target_date_or_none

            try:
                stats = consolidate_date(
                    target_date,
                    manifest,
                    sync_manifest=sync_manifest,
                    dry_run=args.dry_run,
                    force=args.force,
                    local_zips=args.local_zips,
                    max_zips=args.max_zips,
                    workers=args.workers,
                )
                _print_stats(stats)
                for k in total_stats:
                    total_stats[k] += stats.get(k, 0)
                dates_processed += 1
            except Exception as e:
                logger.exception("consolidation_aborted", date=target_date, error=str(e))
                traceback.print_exc()
                # Continue to next date instead of aborting the entire run
                dates_processed += 1
                continue

    else:
        target_date = datetime.now(UTC).date().strftime("%Y-%m-%d")
        try:
            stats = consolidate_date(
                target_date,
                manifest,
                sync_manifest=sync_manifest,
                dry_run=args.dry_run,
                force=args.force,
                local_zips=args.local_zips,
                max_zips=args.max_zips,
                workers=args.workers,
            )
            _print_stats(stats)
            for k in total_stats:
                total_stats[k] += stats.get(k, 0)
        except Exception as e:
            logger.exception("consolidation_aborted", error=str(e))
            traceback.print_exc()
            return 1

    # Output total stats

    # Set GitHub Actions output: did we add any files?
    files_added = total_stats["parquets_created"] > 0

    # Output for GitHub Actions conditional triggers
    if os_env := os.getenv("GITHUB_OUTPUT"):
        with Path(os_env).open("a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")
            f.write(f"consolidate_zips={total_stats['zips_processed']}\n")
            f.write(f"consolidate_records={total_stats['records']}\n")
            f.write(f"consolidate_parquets={total_stats['parquets_created']}\n")
            f.write(f"consolidate_uploaded={total_stats['uploaded']}\n")
            f.write(f"consolidate_uploaded_mb={total_stats['uploaded_mb']:.1f}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
