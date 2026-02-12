#!/usr/bin/env python3
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
import configparser
import decimal
import hashlib
import json
import os
import tempfile
import time
import unicodedata
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from typing import Any


# Disable strict decimal traps that cause crashes in ibis/sqlglot
# See: https://github.com/ibis-project/ibis/issues/9638 (similar)
# This is required because sqlglot may attempt to convert "binary_double_nan"
# which triggers InvalidOperation if traps are enabled.
decimal.getcontext().traps[decimal.InvalidOperation] = False

import duckdb  # noqa: E402
import httpx  # noqa: E402
import ibis  # noqa: E402
import structlog  # noqa: E402

from causaganha.config import TRIBUNAIS  # noqa: E402
from causaganha.storage.djen_schema import (  # noqa: E402
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


# Cache for tribunal stopped checks (tribunal -> date -> bool)
_TRIBUNAL_STOPPED_CACHE: dict[str, dict[str, bool]] = {}

# Cache for consolidation candidates (list of dates)
_CONSOLIDATION_CANDIDATES: list[str] | None = None

# Internet Archive S3-compatible API endpoint
_IA_S3_URL = "https://s3.us.archive.org"

# Checkpoint state file path
_CHECKPOINT_STATE_FILE = Path("data/consolidate-checkpoint.json")


def _compute_md5(file_path: Path) -> str:
    """Compute hex-encoded MD5 checksum (IA S3 format)."""
    h = hashlib.md5()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_ia_s3_auth() -> str | None:
    """Get IA S3 authorization header value from env vars or config file."""
    access = os.environ.get("IAS3_ACCESS_KEY", "")
    secret = os.environ.get("IAS3_SECRET_KEY", "")
    if access and secret:
        return f"LOW {access}:{secret}"
    # Fall back to config file (created by CI workflow)
    config_path = Path.home() / ".config" / "internetarchive" / "ia.ini"
    if config_path.exists():
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        access = cfg.get("s3", "access", fallback="")
        secret = cfg.get("s3", "secret", fallback="")
        if access and secret:
            return f"LOW {access}:{secret}"
    return None


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
        logger.error("checkpoint_save_failed", error=str(e))


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


def fetch_manifest_records() -> list[dict]:
    """Download and return all manifest records from Internet Archive.

    Returns empty list on error.
    """
    manifest_url = "https://archive.org/download/causaganha-catalog/manifest.parquet"
    logger.info("fetching_manifest", url=manifest_url)

    try:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        # Download manifest
        with httpx.Client() as client:
            resp = client.get(manifest_url, timeout=60, follow_redirects=True)
            if resp.status_code != 200:
                logger.warning("manifest_download_failed", status=resp.status_code)
                return []
            with tmp_path.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

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
            try:
                tmp_path.unlink()
            except Exception:
                pass

        return records

    except Exception as e:
        logger.warning("fetch_manifest_failed", error=str(e))
        return []


def fetch_consolidation_candidates(manifest: list[dict] | None = None) -> list[str]:
    """Fetch dates needing consolidation from catalog manifest.

    If manifest is provided (in-memory), queries it using DuckDB.
    Otherwise, downloads it from IA first.
    Returns dates sorted by date descending (newest first).
    """
    if manifest is None:
        manifest_url = "https://archive.org/download/causaganha-catalog/manifest.parquet"
        logger.info("fetching_consolidation_candidates_from_url", url=manifest_url)
        # For simplicity in this case, we use the URL directly in DuckDB
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        try:
            query = """
                SELECT date
                FROM read_parquet('https://archive.org/download/causaganha-catalog/manifest.parquet')
                GROUP BY date
                HAVING SUM(CASE WHEN file_type='zip' THEN 1 ELSE 0 END) > 0
                   AND SUM(CASE WHEN file_type='parquet' THEN 1 ELSE 0 END) = 0
                ORDER BY date DESC
            """
            result = con.execute(query).fetchall()
            return [str(r[0]) for r in result]
        except Exception as e:
            logger.warning("fetch_candidates_failed", error=str(e))
            return []
        finally:
            con.close()

    # Use in-memory manifest
    logger.info("fetching_consolidation_candidates_from_memory", records=len(manifest))
    con = duckdb.connect()
    try:
        # Load manifest list into a DuckDB table
        # We only need date and file_type
        df_data = [{"date": m["date"], "file_type": m["file_type"]} for m in manifest]
        import pandas as pd

        df = pd.DataFrame(df_data)  # noqa: F841

        query = """
            SELECT date
            FROM df
            GROUP BY date
            HAVING SUM(CASE WHEN file_type='zip' THEN 1 ELSE 0 END) > 0
               AND SUM(CASE WHEN file_type='parquet' THEN 1 ELSE 0 END) = 0
            ORDER BY date DESC
        """
        result = con.execute(query).fetchall()
        return [str(r[0]) for r in result]
    except Exception as e:
        logger.warning("fetch_candidates_failed_memory", error=str(e))
        return []
    finally:
        con.close()


class CheckpointManager:
    """Manages local checkpoint state for backfill progress."""

    def __init__(self, filepath: Path):
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
SCHEMA_VERSION = "3"
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

logger = structlog.get_logger()


def parse_deadline(duration_str: str) -> int:
    """Parse a deadline string (e.g. '10m', '600s') into seconds."""
    if not duration_str:
        return 0
    duration_str = duration_str.strip().lower()
    try:
        if duration_str.endswith("m"):
            return int(float(duration_str[:-1]) * 60)
        if duration_str.endswith("s"):
            return int(float(duration_str[:-1]))
        return int(float(duration_str))
    except ValueError:
        return 0


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
        tribunal = parts[-1] if len(parts) >= 4 else "UNKNOWN"
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
    date: str, manifest: list[dict] | None = None
) -> tuple[list[dict[str, Any]], int]:
    """Find all ZIP files for a specific date on IA.

    If manifest is provided, use it (fast). Otherwise use IA metadata API (slow).
    """
    logger.info("listing_zips", date=date)
    item_id = f"djen-{date}"
    zips: list[dict[str, Any]] = []

    # 1. Use manifest if available (fast)
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
                            "size": 0,  # manifest doesn't have size currently
                        }
                    )
        return zips, len(present)

    # 2. Use IA metadata API (slow fallback)
    try:
        # Use IA metadata API
        url = f"https://archive.org/metadata/{item_id}"
        response = httpx.get(url, timeout=60)

        if response.status_code == 200:
            data = response.json()
            files = data.get("files", [])

            # Identify what's on IA
            present = set()
            for file_info in files:
                filename = file_info.get("name", "")
                if filename.endswith((".zip", ".absent")):
                    parts = filename.replace(".zip", "").replace(".absent", "").split("-")
                    tribunal = parts[-1] if len(parts) >= 4 else "UNKNOWN"
                    present.add(tribunal)

                    if filename.endswith(".zip"):
                        zips.append(
                            {
                                "filename": filename,
                                "tribunal": tribunal,
                                "item_id": item_id,
                                "size": file_info.get("size", 0),
                            },
                        )

            # Return both zip list and completion status
            return zips, len(present)
        logger.warning("metadata_fetch_failed", item_id=item_id, status=response.status_code)

    except Exception as e:
        logger.warning("list_failed", item_id=item_id, error=str(e))

    logger.info("zips_found", count=len(zips), date=date)
    return zips, 0


def download_zip(item_id: str, filename: str, output_path: Path) -> bool:
    """Download ZIP from Internet Archive using httpx with retries."""
    url = f"https://archive.org/download/{item_id}/{filename}"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
                if response.status_code == 200:
                    with output_path.open("wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                    return output_path.exists() and output_path.stat().st_size > 0
                if response.status_code in [502, 503, 504]:
                    logger.warning(
                        "download_server_error",
                        filename=filename,
                        status=response.status_code,
                        attempt=attempt + 1,
                    )
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                logger.warning(
                    "download_http_error",
                    filename=filename,
                    status=response.status_code,
                )
                return False
        except Exception as e:
            logger.warning("download_failed", filename=filename, error=str(e), attempt=attempt + 1)
            time.sleep(2**attempt)
    return False


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
)


def _load_and_transform(
    con: ibis.BaseBackend,
    ndjson_dir: Path,
    item_id: str,
) -> dict[str, int]:
    """Load raw per-tribunal NDJSON into DuckDB, produce all 9 tables via Ibis.

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


def upload_to_ia(client: httpx.Client, item_id: str, file_path: Path, date_str: str) -> bool:
    """Upload file to Internet Archive via httpx (direct HTTP PUT).

    CRITICAL: We use httpx instead of 'ia' CLI for consistency with collect.py
    and better performance (no shell out + re-auth per file).

    boto3 is incompatible with IA S3 because it forces 'x-amz-meta-*' headers,
    while IA requires 'x-archive-meta-*'. See PR #348 for details.
    """
    filename = file_path.name
    url = f"{_IA_S3_URL}/{item_id}/{filename}"
    content_md5 = _compute_md5(file_path)

    headers = {
        "Content-MD5": content_md5,
        "x-archive-auto-make-bucket": "1",
        "x-archive-queue-derive": "0",
        "x-archive-meta-collection": "opensource",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-title": f"DJEN Consolidated - {date_str}",
        "x-archive-meta-description": (
            "Consolidated Parquet files from Brazilian court communications."
        ),
        "x-archive-meta-subject": "brazilian-law;djen;legal;judiciary;open-data",
        "x-archive-meta-creator": "CausaGanha",
        "x-archive-meta-date": date_str,
    }

    # Retry strategy with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with file_path.open("rb") as f:
                response = client.put(url, content=f, headers=headers, timeout=300)
            if response.is_success:
                return True
            logger.warning(
                "upload_http_error",
                item_id=item_id,
                file=filename,
                status=response.status_code,
                attempt=attempt + 1,
            )
            if response.status_code < 500:
                return False  # Client error — don't retry
        except Exception as e:
            logger.warning(
                "upload_error",
                item_id=item_id,
                error=str(e),
                attempt=attempt + 1,
            )
        if attempt < max_retries - 1:
            time.sleep(5 * (attempt + 1))
    return False


def _upload_marker(client: httpx.Client, item_id: str, date_str: str) -> bool:
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
        success = upload_to_ia(client, item_id, marker_path, date_str)

        # Cleanup temp file
        try:
            marker_path.unlink()
        except Exception:
            pass

        return success
    except Exception as e:
        logger.error("marker_upload_failed", item_id=item_id, error=str(e))
        return False


def _is_tribunal_stopped(
    tribunal: str, target_date: date, manifest: list[dict] | None = None, absent_threshold: int = 60
) -> bool:
    """Check if a tribunal has been absent for 60+ consecutive days before target_date.

    If manifest is provided, use it to check (fast).
    Otherwise, scans the last N days backward from target_date using IA metadata API (slow).
    """
    date_str = target_date.strftime("%Y-%m-%d")

    # Check cache
    if tribunal in _TRIBUNAL_STOPPED_CACHE:
        if date_str in _TRIBUNAL_STOPPED_CACHE[tribunal]:
            return _TRIBUNAL_STOPPED_CACHE[tribunal][date_str]
    else:
        _TRIBUNAL_STOPPED_CACHE[tribunal] = {}

    # 1. Manifest-based check (fast)
    if manifest:
        # Build lookup for this tribunal if not in cache
        # Note: We use a simple lookup for speed
        trib_key = f"_lookup_{tribunal}"
        if trib_key not in _TRIBUNAL_STOPPED_CACHE:
            _TRIBUNAL_STOPPED_CACHE[trib_key] = {}
            for m in manifest:
                if m["tribunal"] == tribunal:
                    d = m["date"]
                    if d not in _TRIBUNAL_STOPPED_CACHE[trib_key]:
                        _TRIBUNAL_STOPPED_CACHE[trib_key][d] = []
                    _TRIBUNAL_STOPPED_CACHE[trib_key][d].append(m["file_type"])

        tribunal_files = _TRIBUNAL_STOPPED_CACHE[trib_key]

        for days_back in range(1, absent_threshold + 1):
            check_date = target_date - timedelta(days=days_back)
            if check_date.weekday() >= 5:  # skip weekends
                continue

            check_date_str = check_date.strftime("%Y-%m-%d")

            # If date not in manifest at all, can't conclude stopped
            if check_date_str not in tribunal_files:
                result = False
                _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
                return result

            # If we find a .zip (not just .absent), tribunal is active
            if "zip" in tribunal_files[check_date_str]:
                result = False
                _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
                return result

            # If neither zip nor absent, can't conclude stopped
            if "absent" not in tribunal_files[check_date_str]:
                result = False
                _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
                return result

        result = True
        _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
        return result

    # 2. IA Metadata API-based check (slow fallback)
    logger.info("is_tribunal_stopped_api_fallback", tribunal=tribunal, date=date_str)
    for days_back in range(1, absent_threshold + 1):
        check_date = target_date - timedelta(days=days_back)
        if check_date.weekday() >= 5:  # skip weekends
            continue

        check_date_str = check_date.strftime("%Y-%m-%d")
        item_id = f"djen-{check_date_str}"
        url = f"https://archive.org/metadata/{item_id}"

        try:
            resp = httpx.get(url, timeout=10)
            if resp.status_code != 200:
                # Can't verify - assume not stopped
                result = False
                _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
                return result

            files = resp.json().get("files", [])
            tribunal_found = False

            for f in files:
                if not isinstance(f, dict):
                    continue
                name = f.get("name", "")

                # Check if this file belongs to the tribunal
                if tribunal in name:
                    # If we find a .zip (not .absent), tribunal is active
                    if name.endswith(".zip"):
                        result = False
                        _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
                        return result
                    # If .absent, mark as found and continue checking other days
                    if name.endswith(".absent"):
                        tribunal_found = True
                        break

            # If no file for this tribunal on this day, can't conclude stopped
            if not tribunal_found:
                result = False
                _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
                return result

        except Exception:
            # On error, assume not stopped (conservative)
            result = False
            _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
            return result

    # All checked days had .absent marker - tribunal is stopped
    result = True
    _TRIBUNAL_STOPPED_CACHE[tribunal][date_str] = result
    return result


def _needs_consolidation(
    date_str: str, manifest: list[dict] | None = None, *, must_be_complete: bool = False
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
                if trib not in present_tribunais:
                    if not _is_tribunal_stopped(trib, target_d, manifest):
                        return False
            return True

        return True

    # 2. IA metadata API fallback
    item_id = f"djen-{date_str}"
    url = f"https://archive.org/metadata/{item_id}"
    try:
        resp = httpx.get(url, timeout=30)
        if resp.status_code != 200:
            return False
        files = resp.json().get("files", [])
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
                if len(parts) >= 4:
                    present_tribunais.add(parts[-1])

            # Check for any .parquet file or the sentinel marker as proof of consolidation
            if name.endswith(".parquet") or name == "_consolidated.marker":
                has_consolidated = True

        if not (has_zips and not has_consolidated):
            return False

        if must_be_complete:
            # Count only non-stopped tribunals
            target_d = date.fromisoformat(date_str)
            active_tribunals = []

            for trib in TRIBUNAIS:
                if trib not in present_tribunais:
                    # Check if this tribunal is stopped (60+ days absent)
                    if not _is_tribunal_stopped(trib, target_d):
                        # Not stopped - we need it
                        active_tribunals.append(trib)

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

        return True
    except Exception:
        return False


def _all_tribunals_stopped(target_date: date, manifest: list[dict] | None = None) -> bool:
    """Check if ALL tribunals are stopped (60+ days absent) at target_date.

    This is the natural stopping condition for backfill - when there's no more
    historical data from any tribunal.
    """
    return all(_is_tribunal_stopped(tribunal, target_date, manifest) for tribunal in TRIBUNAIS)


def find_next_unconsolidated(
    manifest: list[dict] | None = None, checkpoint_file: Path | None = None
) -> str | None:
    """Find the most recent date needing consolidation.

    First tries to fetch candidates from the catalog manifest (fast).
    Falls back to walking backward from today (slow) if manifest is unavailable.

    Returns the date string or None if everything is consolidated.
    """
    global _CONSOLIDATION_CANDIDATES

    # 1. Try manifest-based discovery (fast, minimal API calls)
    if _CONSOLIDATION_CANDIDATES is None:
        _CONSOLIDATION_CANDIDATES = fetch_consolidation_candidates(manifest)

    if _CONSOLIDATION_CANDIDATES:
        while _CONSOLIDATION_CANDIDATES:
            candidate = _CONSOLIDATION_CANDIDATES.pop(0)
            # We found a candidate from manifest. It definitely has ZIPs and no parquets.
            # We return it directly. consolidate_date will verify completeness.
            logger.info("candidate_from_manifest", date=candidate)
            return candidate

    # 2. Fallback: Walk backward from today (slow, heavy API usage)
    if checkpoint_file is None:
        checkpoint_file = Path(".backfill_checkpoint.json")

    checkpoint = CheckpointManager(checkpoint_file)
    last_checked = checkpoint.load()

    today = date.today()
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

    while days_ago < max_iterations:
        d = today - timedelta(days=days_ago)
        d_str = d.strftime("%Y-%m-%d")

        # Skip weekends
        if d.weekday() >= 5:
            days_ago += 1
            continue

        # Check if we've gone back far enough (all tribunals stopped)
        if _all_tribunals_stopped(d, manifest):
            logger.info(
                "backfill_complete", date=d_str, days_ago=days_ago, reason="all_tribunals_stopped"
            )
            return None

        # Backfill requires completeness — only consolidate when everything is gathered
        if _needs_consolidation(d_str, manifest, must_be_complete=True):
            logger.info("unconsolidated_date_found", date=d_str, days_ago=days_ago)
            checkpoint.save(d_str)
            return d_str

        checkpoint.save(d_str)
        days_ago += 1

    # Safety limit reached
    logger.warning("backfill_max_iterations", max_iterations=max_iterations)
    return None


def _export_and_upload_table(
    table_name: str,
    con: ibis.BaseBackend,
    output_dir: Path,
    item_id: str,
    client: httpx.Client,
    date_str: str,
    *,
    dry_run: bool,
) -> tuple[bool, float, int]:
    """Export single table to Parquet and upload. Returns (success, size_mb, uploaded_count)."""
    size_mb = 0.0
    try:
        t = con.table(table_name)
        count = t.count().to_pandas()
        if count == 0:
            return False, 0.0, 0

        output_path = output_dir / f"{table_name}.parquet"
        con.raw_sql(
            f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET, COMPRESSION ZSTD)",
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "parquet_created",
            table=table_name,
            rows=count,
            size_mb=f"{size_mb:.1f}",
        )

        # Upload if not dry run
        uploaded = 0
        if not dry_run and upload_to_ia(client, item_id, output_path, date_str):
            uploaded = 1
            logger.info("uploaded", table=table_name)

        return True, size_mb, uploaded
    except Exception as e:
        logger.error("parquet_export_failed", table=table_name, error=str(e))
        return False, 0.0, 0


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
        import shutil

        try:
            shutil.copy2(zip_entry["local_path"], zip_path)
        except Exception as e:
            logger.warning("local_copy_failed", filename=filename, error=str(e))
            return 0, 0
    elif not download_zip(item_id, filename, zip_path):
        logger.warning("download_failed", filename=filename)
        return 0, 0

    # Extract
    records = extract_json_from_zip(zip_path)
    if not records:
        logger.warning("no_records_found", filename=filename)
        try:
            zip_path.unlink()
        except Exception:
            pass
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
        logger.error("ndjson_write_failed", file=ndjson_filename, error=str(e))
        return 0, 0

    try:
        zip_path.unlink()
    except Exception:
        pass

    return 1, len(records)


def consolidate_date(
    date: str,
    manifest: list[dict] | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    local_zips: str | None = None,
    max_zips: int = 0,
    workers: int = 16,
) -> dict[str, int | float]:
    """Consolidate all tribunals for a date into single Parquet files.

    Args:
        date: Date string in YYYY-MM-DD format.
        manifest: In-memory manifest of IA files.
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
        zips, present_count = list_zips_for_date(date, manifest)

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

    # Use Ibis with DuckDB backend
    con = ibis.duckdb.connect()
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
                    logger.error("zip_processing_error", zip=zip_filename, error=str(e))

        # Phase 2: Ibis-driven transformation (UDFs, unnest, distinct)
        if stats["records"] > 0:
            table_counts = _load_and_transform(con, ndjson_dir, item_id)
            logger.info("transform_complete", tables=table_counts)

        # Phase 3: Export to Parquet and upload (parallel for 2-3x speedup)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        logger.info("exporting_parquets", table_count=len(TABLES))

        # Resolve IA S3 credentials for upload client
        ia_auth = _get_ia_s3_auth()
        upload_headers = {"Authorization": ia_auth} if ia_auth else {}
        if not ia_auth and not dry_run:
            logger.warning(
                "ia_credentials_not_found",
                hint="Set IAS3_ACCESS_KEY/IAS3_SECRET_KEY or run `ia configure`",
            )

        # Create httpx client for uploads (connection pooling across parallel uploads)
        with httpx.Client(timeout=300, headers=upload_headers) as client:
            # Parallel export + upload with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(
                        _export_and_upload_table,
                        table_name,
                        con,
                        output_dir,
                        item_id,
                        client,
                        date,
                        dry_run=dry_run,
                    ): table_name
                    for table_name in TABLES
                }

                for future in as_completed(futures):
                    table_name = futures[future]
                    try:
                        success, size_mb, uploaded = future.result()
                        if success:
                            stats["parquets_created"] += 1
                            stats["uploaded"] += uploaded
                            stats["uploaded_mb"] += size_mb
                    except Exception as e:
                        logger.error("table_export_error", table=table_name, error=str(e))

            # Phase 4: Upload consolidation marker
            if stats["parquets_created"] > 0 and not dry_run:
                if _upload_marker(client, item_id, date):
                    logger.info("marker_uploaded", item_id=item_id)
                    # Mark date as complete in checkpoint
                    mark_date_complete(date)
                else:
                    logger.warning("marker_upload_failed", item_id=item_id)

    return stats


def _print_stats(stats: dict[str, int]) -> None:
    print()
    print("=" * 40)
    print("CONSOLIDATION SUMMARY")
    print("=" * 40)
    print(f"  ZIPs processed:   {stats['zips_processed']}")
    print(f"  Records:          {stats['records']}")
    print(f"  Parquets created: {stats['parquets_created']}")
    print(f"  Uploaded:         {stats['uploaded']}")
    print(f"  Uploaded MB:      {stats.get('uploaded_mb', 0):.1f}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate DJEN ZIPs to daily Parquets")
    parser.add_argument("--date", help="Date to consolidate (YYYY-MM-DD)")
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

    # Fetch manifest once if in backfill mode or scanning needed
    manifest = None
    if args.backfill or not args.date:
        manifest = fetch_manifest_records()
        if manifest:
            print(f"Manifest loaded: {len(manifest)} records")
        else:
            print("Warning: Could not load manifest. Falling back to API checks (slow).")

    if args.date:
        # Explicit date — existing behaviour
        print(f"Consolidating DJEN data for {args.date}...")
        try:
            stats = consolidate_date(
                args.date,
                manifest,
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
            logger.error("consolidation_aborted", error=str(e))
            import traceback

            traceback.print_exc()
            return 1

    elif args.backfill:
        # Backfill: process multiple unconsolidated dates until deadline
        print(f"Backfill mode: scanning for unconsolidated dates (deadline: {deadline_sec}s)...")
        dates_processed = 0

        while True:
            # Check deadline - leave 120s margin for upload completion
            if deadline_sec > 0:
                elapsed = time.time() - start_time
                if elapsed > deadline_sec - 120:
                    print(f"Deadline approaching ({elapsed:.0f}s / {deadline_sec}s). Stopping after {dates_processed} dates.")
                    break

            target_date_or_none = find_next_unconsolidated(manifest)
            if target_date_or_none is None:
                print("Backfill complete: all dates consolidated or all tribunals stopped.")
                break

            target_date = target_date_or_none
            print(f"\n[Backfill {dates_processed + 1}] Consolidating DJEN data for {target_date}...")

            try:
                stats = consolidate_date(
                    target_date,
                    manifest,
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
                logger.error("consolidation_aborted", date=target_date, error=str(e))
                import traceback

                traceback.print_exc()
                # Continue to next date instead of aborting the entire run
                dates_processed += 1
                continue

    else:
        # Default: today
        target_date = date.today().strftime("%Y-%m-%d")
        print(f"Consolidating DJEN data for {target_date}...")
        try:
            stats = consolidate_date(
                target_date,
                manifest,
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
            logger.error("consolidation_aborted", error=str(e))
            import traceback

            traceback.print_exc()
            return 1

    # Output total stats
    print()
    print("=" * 40)
    print("TOTAL RUN SUMMARY")
    print("=" * 40)
    print(f"  ZIPs processed:   {total_stats['zips_processed']}")
    print(f"  Records:          {total_stats['records']}")
    print(f"  Parquets created: {total_stats['parquets_created']}")
    print(f"  Uploaded:         {total_stats['uploaded']}")
    print(f"  Uploaded MB:      {total_stats['uploaded_mb']:.1f}")

    # Set GitHub Actions output: did we add any files?
    files_added = total_stats["parquets_created"] > 0
    print(f"\n  Files added: {files_added}")

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
    exit(main())
