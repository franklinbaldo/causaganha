"""Daily packaging and indexing for self-contained DataJud process backups in Internet Archive.

Implements the IA transparent-unzip pattern from `franklinbaldo/ficha`:
- Packs full process documents (capa + all movimientos) into daily ZIP archives:
  `{tribunal}_{YYYY-MM-DD}.zip` containing `{cnj}.json.gz` (or `{cnj}.json`).
- Consumers can retrieve any complete process in 1 GET request via the IA transparent unzip URL:
  `https://archive.org/download/{item}/{zip_file}/{cnj}.json.gz`.
- Updates the resolution index (`indice_processos_{tribunal}.parquet`) pointing each CNJ
  to the latest daily ZIP archive containing its full snapshot.
"""

from __future__ import annotations

import gzip
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from datajud.models import normalizar_cnj


if TYPE_CHECKING:
    from collections.abc import Sequence


log = structlog.get_logger()

DEFAULT_DAILY_DIR = Path("data/datajud/daily")
DEFAULT_INDEX_DIR = Path("data/datajud/index")

INDEX_SCHEMA = pa.schema(
    [
        pa.field("numero_processo", pa.string()),
        pa.field("tribunal", pa.string()),
        pa.field("grau", pa.string()),
        pa.field("data_hora_ultima_atualizacao", pa.string()),
        pa.field("zip_file", pa.string()),
        pa.field("atualizado_em", pa.string()),
    ]
)


def pack_daily_zip(
    documents: Sequence[dict[str, Any]],
    tribunal: str,
    target_date: str,
    output_dir: Path = DEFAULT_DAILY_DIR,
    *,
    compress_internal_json: bool = True,
) -> tuple[Path, int]:
    """Package full process documents into a daily ZIP archive for Internet Archive.

    Args:
        documents: Raw Elasticsearch process documents (each containing numeroProcesso,
            capa metadata, and movimentos array).
        tribunal: Tribunal identifier (e.g. "tjro").
        target_date: Date string formatted as "YYYY-MM-DD".
        output_dir: Directory where the daily ZIP is saved.
        compress_internal_json: If True, each entry inside the ZIP is `{cnj}.json.gz`
            for double-density storage.

    Returns:
        (zip_path, process_count)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tribunal_slug = tribunal.lower()
    zip_path = output_dir / f"{tribunal_slug}_{target_date}.zip"

    # Deduplicate within batch keeping latest dataHoraUltimaAtualizacao
    deduped: dict[str, dict[str, Any]] = {}
    for doc in documents:
        raw_cnj = doc.get("numeroProcesso", "")
        cnj = normalizar_cnj(raw_cnj) or raw_cnj
        if not cnj:
            continue
        current = deduped.get(cnj)
        if current is None or (doc.get("dataHoraUltimaAtualizacao") or "") >= (
            current.get("dataHoraUltimaAtualizacao") or ""
        ):
            deduped[cnj] = doc

    if not deduped:
        return zip_path, 0

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cnj, doc in deduped.items():
            payload = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if compress_internal_json:
                buf = io.BytesIO()
                with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0.0) as gz:
                    gz.write(payload)
                entry_name = f"{cnj}.json.gz"
                zf.writestr(entry_name, buf.getvalue())
            else:
                entry_name = f"{cnj}.json"
                zf.writestr(entry_name, payload)

    log.info(
        "datajud_daily_zip_packed",
        tribunal=tribunal_slug,
        target_date=target_date,
        zip_path=str(zip_path),
        processes=len(deduped),
    )
    return zip_path, len(deduped)


def update_resolution_index(
    index_path: Path,
    documents: Sequence[dict[str, Any]],
    zip_filename: str,
    tribunal: str,
) -> int:
    """Upsert pointers into the resolution index Parquet table.

    Points each CNJ to the latest daily ZIP archive containing its full state.

    Returns:
        Total number of indexed processes in the updated index table.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tribunal_slug = tribunal.lower()
    now_iso = datetime.now(UTC).isoformat(timespec="seconds")

    existing_rows: dict[str, dict[str, Any]] = {}
    if index_path.exists():
        existing_table = pq.read_table(index_path)
        for r in existing_table.to_pylist():
            existing_rows[r["numero_processo"]] = r

    for doc in documents:
        raw_cnj = doc.get("numeroProcesso", "")
        cnj = normalizar_cnj(raw_cnj) or raw_cnj
        if not cnj:
            continue

        updated_at = doc.get("dataHoraUltimaAtualizacao") or ""
        current = existing_rows.get(cnj)

        if current is None or updated_at >= (current.get("data_hora_ultima_atualizacao") or ""):
            existing_rows[cnj] = {
                "numero_processo": cnj,
                "tribunal": tribunal_slug,
                "grau": doc.get("grau") or "G1",
                "data_hora_ultima_atualizacao": updated_at,
                "zip_file": zip_filename,
                "atualizado_em": now_iso,
            }

    sorted_rows = sorted(existing_rows.values(), key=lambda r: r["numero_processo"])
    table = pa.Table.from_pylist(sorted_rows, schema=INDEX_SCHEMA)
    pq.write_table(table, index_path, compression="zstd")

    log.info(
        "datajud_index_updated",
        tribunal=tribunal_slug,
        index_path=str(index_path),
        total_indexed=len(sorted_rows),
    )
    return len(sorted_rows)


def export_daily_locators(
    zip_path: Path,
    tribunal: str,
    *,
    output_path: Path | None = None,
) -> Path:
    """Publish exact IA locators for documents actually present in the daily ZIP.

    Unlike the legacy single-row-per-CNJ resolution index, this feed includes
    the source document identity and does not pretend that missing grades exist.
    The original document bytes and member names are left unchanged.
    """
    tribunal_slug = tribunal.lower()
    target = output_path or zip_path.with_suffix(".locators.jsonl")
    item = f"datajud-{tribunal_slug}"
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not (name.endswith(".json.gz") or name.endswith(".json")):
                continue
            content = archive.read(name)
            if name.endswith(".gz"):
                content = gzip.decompress(content)
            doc = json.loads(content)
            cnj = normalizar_cnj(doc.get("numeroProcesso", ""))
            degree = doc.get("grau")
            original_id = doc.get("id") or doc.get("_id")
            updated = doc.get("dataHoraUltimaAtualizacao")
            if not cnj or not degree or not original_id or not updated:
                raise ValueError(f"Incomplete DataJud source identity in {name}")
            rows.append({
                "numero_processo": cnj,
                "tribunal": tribunal.upper(),
                "grau": str(degree),
                "documento_id": str(original_id),
                "item_ia": item,
                "arquivo_zip": zip_path.name,
                "membro": name,
                "atualizado_em": str(updated),
            })
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in sorted(rows, key=lambda r: (
                    r["numero_processo"], r["grau"], r["documento_id"]
                ))),
        encoding="utf-8",
    )
    return target
