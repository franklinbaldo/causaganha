"""TJRO JURIS CLI — crawl, upload, status, consolidate."""

from __future__ import annotations

import asyncio
import datetime as _dt
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated


if TYPE_CHECKING:
    from pathlib import Path

import anyio
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import structlog
import typer

from tjro_juris import archive as ia_archive
from tjro_juris.client import TIPOS, clean_html
from tjro_juris.crawler import crawl_all
from tjro_juris.dedup import consolidate_year
from tjro_juris.manifest import ManifestJuris, ManifestJurisEntry


log = structlog.get_logger()
app = typer.Typer(name="tjro-juris", help="TJRO JURIS scraping and archival.")

_MANIFEST_NAME = "tjro-juris-manifest.csv"
_MIN_DATE_LEN = 10

_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("id_documento", pa.int64()),
        pa.field("nr_processo", pa.string()),
        pa.field("tipo", pa.string()),
        pa.field("classe_judicial", pa.string()),
        pa.field("orgao", pa.string()),
        pa.field("relator", pa.string()),
        pa.field("sistema_origem", pa.string()),
        pa.field("data_julgamento", pa.date32()),
        pa.field("texto_limpo", pa.string()),
        pa.field("url_portal", pa.string()),
        pa.field("extraido_em", pa.string()),
    ]
)


def _manifest_path(data_dir: Path) -> Path:
    return data_dir / _MANIFEST_NAME


def _parquet_path(data_dir: Path, tipo: str, year_month: str) -> Path:
    year = year_month[:4]
    safe_tipo = tipo.replace(" ", "_").replace("/", "_")
    return data_dir / year / safe_tipo / f"{year_month}.parquet"


def _normalize_date(dt_raw: str) -> str | None:
    """Normalize date string to YYYY-MM-DD."""
    if not dt_raw:
        return None
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", dt_raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return dt_raw[:_MIN_DATE_LEN] if len(dt_raw) >= _MIN_DATE_LEN else dt_raw


def _to_row(src: dict) -> dict:
    """Map a crawler-normalized doc to canonical parquet schema.

    Accepts the dict produced by crawler._extract_doc() which already uses
    canonical field names (id_documento, classe_judicial, orgao, etc.).
    """
    dt_raw = src.get("data_julgamento") or ""
    return {
        "id_documento": src.get("id_documento"),
        "nr_processo": src.get("nr_processo") or "",
        "tipo": src.get("tipo") or "",
        "classe_judicial": src.get("classe_judicial") or "",
        "orgao": src.get("orgao") or "",
        "relator": src.get("relator") or "",
        "sistema_origem": src.get("sistema_origem") or "",
        "data_julgamento": _normalize_date(dt_raw),
        "texto_limpo": src.get("texto_limpo") or clean_html(src.get("ds_modelo_documento") or ""),
        "url_portal": src.get("url_portal") or "",
        "extraido_em": src.get("extraido_em") or datetime.now(UTC).isoformat(),
    }


def _parse_date(v: str | None) -> _dt.date | None:
    """Parse ISO date string to date object."""
    if not v:
        return None
    try:
        return _dt.date.fromisoformat(v)
    except ValueError:
        return None


def _rows_to_parquet(rows: list[dict], out: Path) -> None:
    """Write list of row dicts to a parquet file using pyarrow."""
    arrays: dict[str, list] = {f.name: [] for f in _PARQUET_SCHEMA}
    for row in rows:
        for field in _PARQUET_SCHEMA:
            val = row.get(field.name)
            if field.name == "id_documento":
                arrays[field.name].append(int(val) if val is not None else None)
            elif field.name == "data_julgamento":
                arrays[field.name].append(val)
            else:
                arrays[field.name].append(str(val) if val is not None else None)

    arrow_cols = []
    for field in _PARQUET_SCHEMA:
        raw = arrays[field.name]
        if field.type == pa.date32():
            arrow_cols.append(pa.array([_parse_date(v) for v in raw], type=pa.date32()))
        else:
            arrow_cols.append(pa.array(raw, type=field.type))

    table = pa.table(
        dict(zip(_PARQUET_SCHEMA.names, arrow_cols, strict=True)), schema=_PARQUET_SCHEMA
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)


@app.command()
def crawl(
    data_dir: Annotated[Path, typer.Argument(help="Directory to store parquet files")],
    tipo: Annotated[
        list[str] | None, typer.Option("--tipo", "-t", help="Filter to these tipos")
    ] = None,
    ano: Annotated[int | None, typer.Option("--ano", "-a", help="Only crawl this year")] = None,
) -> None:
    """Crawl JURIS and save as parquet files per (tipo, mes_ano)."""
    manifest = ManifestJuris.load_local(_manifest_path(data_dir))
    tipos_to_crawl = tipo or TIPOS

    now = datetime.now(UTC)
    if ano is not None:
        start_year = ano
        end_year_month: str | None = f"{ano:04d}-12" if ano < now.year else now.strftime("%Y-%m")
    else:
        start_year = 2010
        end_year_month = None

    for tipo_name, year_month, docs in crawl_all(
        start_year=start_year, end_year_month=end_year_month, tipos=tipos_to_crawl
    ):
        if not docs:
            continue

        rows = [_to_row(d) for d in docs]
        out = _parquet_path(data_dir, tipo_name, year_month)
        _rows_to_parquet(rows, out)
        log.info("parquet_saved", path=str(out), rows=len(rows))

        entry = ManifestJurisEntry(
            tipo=tipo_name,
            mes_ano=year_month,
            ia_status="",
            n_docs=len(docs),
        )
        manifest.upsert(entry)

    manifest.save_local(_manifest_path(data_dir))
    log.info("crawl_done")


@app.command()
def upload(
    data_dir: Annotated[Path, typer.Argument(help="Directory with parquet files")],
) -> None:
    """Upload parquets to Internet Archive."""
    manifest = ManifestJuris.load_local(_manifest_path(data_dir))
    pending = manifest.pending_upload()

    async def _upload_all() -> None:
        for entry in pending:
            pq_path = _parquet_path(data_dir, entry.tipo, entry.mes_ano)
            if not await anyio.Path(pq_path).exists():
                log.warning("parquet_not_found", path=str(pq_path))
                continue
            year = int(entry.mes_ano[:4])
            safe_tipo = entry.tipo.replace(" ", "_").replace("/", "_")
            remote_name = f"{entry.mes_ano}-{safe_tipo}.parquet"
            try:
                await ia_archive.upload_file(pq_path, year, remote_name)
                entry.ia_status = "uploaded"
                manifest.upsert(entry)
            except (httpx.HTTPError, httpx.RequestError, RuntimeError) as exc:
                log.warning(
                    "upload_failed",
                    entry=f"{entry.tipo}/{entry.mes_ano}",
                    error=str(exc),
                )

    asyncio.run(_upload_all())
    manifest.save_local(_manifest_path(data_dir))
    log.info("upload_done", pending=len(pending))


@app.command()
def status(
    data_dir: Annotated[Path, typer.Argument(help="Directory with manifest")],
) -> None:
    """Show manifest status."""
    manifest = ManifestJuris.load_local(_manifest_path(data_dir))
    entries = manifest.all_entries()
    uploaded = sum(1 for e in entries if e.ia_status == "uploaded")
    total = len(entries)
    typer.echo(f"Total entries: {total}")
    typer.echo(f"Uploaded:      {uploaded}")
    typer.echo(f"Pending:       {total - uploaded}")


@app.command()
def consolidate(
    data_dir: Annotated[Path, typer.Argument(help="Directory with parquet files")],
    year: Annotated[int, typer.Argument(help="Year to consolidate")],
) -> None:
    """Consolidate monthly parquets for a year into a single deduplicated file."""
    parquet_files: list[Path] = []
    for tipo_name in TIPOS:
        safe_tipo = tipo_name.replace(" ", "_").replace("/", "_")
        tipo_dir = data_dir / str(year) / safe_tipo
        if tipo_dir.exists():
            parquet_files.extend(sorted(tipo_dir.glob("*.parquet")))

    output = data_dir / str(year) / f"tjro-juris-{year}.parquet"
    count = consolidate_year(parquet_files, output)
    typer.echo(f"Consolidated {count} documents to {output}")


if __name__ == "__main__":
    app()
