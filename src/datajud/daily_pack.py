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

import duckdb
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
    The merge runs in DuckDB over the existing Parquet, so memory scales with
    *documents* (the session), not with the whole index (issue #1708). Rule:
    per CNJ the latest ``dataHoraUltimaAtualizacao`` wins; ties go to the new
    pointer, and among new pointers to the later one.

    Returns:
        Total number of indexed processes in the updated index table.
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tribunal_slug = tribunal.lower()
    now_iso = datetime.now(UTC).isoformat(timespec="seconds")

    new_rows = []
    for doc in documents:
        raw_cnj = doc.get("numeroProcesso", "")
        cnj = normalizar_cnj(raw_cnj) or raw_cnj
        if not cnj:
            continue
        new_rows.append(
            {
                "numero_processo": cnj,
                "tribunal": tribunal_slug,
                "grau": doc.get("grau") or "G1",
                "data_hora_ultima_atualizacao": doc.get("dataHoraUltimaAtualizacao") or "",
                "zip_file": zip_filename,
                "atualizado_em": now_iso,
            }
        )
    new_table = pa.Table.from_pylist(new_rows, schema=INDEX_SCHEMA)
    cols = ", ".join(INDEX_SCHEMA.names)
    tmp_path = index_path.with_name(f".{index_path.name}.tmp")

    con = duckdb.connect()
    try:
        con.execute("SET preserve_insertion_order = false")
        con.register("new_rows", new_table)
        existing = (
            f"SELECT {cols}, 0 AS _ord, file_row_number AS _row "
            f"FROM read_parquet('{index_path.as_posix()}', file_row_number = true) UNION ALL "
            if index_path.exists()
            else ""
        )
        con.execute(
            f"COPY (SELECT {cols} FROM ("
            "  SELECT *, row_number() OVER (PARTITION BY numero_processo ORDER BY "
            "    COALESCE(data_hora_ultima_atualizacao, '') DESC, _ord DESC, _row DESC) AS _rn"
            f"  FROM ({existing}SELECT {cols}, 1 AS _ord, row_number() OVER () AS _row FROM new_rows)"
            ") WHERE _rn = 1 ORDER BY numero_processo"
            f") TO '{tmp_path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)"
        )
    finally:
        con.close()
    tmp_path.replace(index_path)
    total = pq.ParquetFile(index_path).metadata.num_rows

    log.info(
        "datajud_index_updated",
        tribunal=tribunal_slug,
        index_path=str(index_path),
        total_indexed=total,
    )
    return total


class SessionSpool:
    """On-disk spool of the raw documents streamed in one CDC session.

    Keeps only a small pointer per CNJ in memory (latest
    ``dataHoraUltimaAtualizacao`` wins, ties to the later document) and the
    original JSON lines on disk, so a long run no longer holds every document
    in RAM (issue #1708). The daily ZIP and the index are built from it.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
        self._fh = path.open("ab")
        self._pointers: dict[str, tuple[str, int, int, str]] = {}

    def __len__(self) -> int:
        return len(self._pointers)

    def add(self, documents: Sequence[dict[str, Any]]) -> None:
        """Append *documents* to the spool and update the per-CNJ pointers."""
        for doc in documents:
            raw_cnj = doc.get("numeroProcesso", "")
            cnj = normalizar_cnj(raw_cnj) or raw_cnj
            if not cnj:
                continue
            line = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            offset = self._fh.tell()
            self._fh.write(line + b"\n")
            updated = doc.get("dataHoraUltimaAtualizacao") or ""
            current = self._pointers.get(cnj)
            if current is None or updated >= current[0]:
                self._pointers[cnj] = (updated, offset, len(line), doc.get("grau") or "")
        self._fh.flush()

    def close(self) -> None:
        """Close the spool file handle (the file itself stays for packing)."""
        self._fh.close()

    def index_documents(self) -> list[dict[str, str]]:
        """Minimal documents for :func:`update_resolution_index`."""
        return [
            {"numeroProcesso": cnj, "grau": grau or "G1", "dataHoraUltimaAtualizacao": updated}
            for cnj, (updated, _offset, _length, grau) in self._pointers.items()
        ]

    def pack_zip(
        self,
        tribunal: str,
        target_date: str,
        output_dir: Path = DEFAULT_DAILY_DIR,
        *,
        compress_internal_json: bool = True,
    ) -> tuple[Path, int]:
        """Write the daily ZIP from the spool, one entry per CNJ (latest document).

        Entry bytes are the original JSON lines, identical to what
        :func:`pack_daily_zip` writes for the same documents.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        tribunal_slug = tribunal.lower()
        zip_path = output_dir / f"{tribunal_slug}_{target_date}.zip"
        if not self._pointers:
            return zip_path, 0
        if not self._fh.closed:
            self._fh.flush()
        with (
            self.path.open("rb") as src,
            zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf,
        ):
            for cnj, (_updated, offset, length, _grau) in self._pointers.items():
                src.seek(offset)
                payload = src.read(length)
                if compress_internal_json:
                    buf = io.BytesIO()
                    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0.0) as gz:
                        gz.write(payload)
                    zf.writestr(f"{cnj}.json.gz", buf.getvalue())
                else:
                    zf.writestr(f"{cnj}.json", payload)
        log.info(
            "datajud_daily_zip_packed",
            tribunal=tribunal_slug,
            target_date=target_date,
            zip_path=str(zip_path),
            processes=len(self._pointers),
        )
        return zip_path, len(self._pointers)


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
                msg = f"Incomplete DataJud source identity in {name}"
                raise ValueError(msg)
            rows.append(
                {
                    "numero_processo": cnj,
                    "tribunal": tribunal.upper(),
                    "grau": str(degree),
                    "documento_id": str(original_id),
                    "item_ia": item,
                    "arquivo_zip": zip_path.name,
                    "membro": name,
                    "atualizado_em": str(updated),
                }
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in sorted(
                rows, key=lambda r: (r["numero_processo"], r["grau"], r["documento_id"])
            )
        ),
        encoding="utf-8",
    )
    return target
