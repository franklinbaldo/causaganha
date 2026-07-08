"""DataJud CLI — enrich, facetas, status.

Manual execution
----------------
Enrich known CNJs with official capa + movimentos (CNJs come from local
source parquets — processos_unificados, TJRO JURIS, STJ — or explicitly)::

    uv run datajud enrich --tribunal tjro --limit 200 --skip-upload
    uv run datajud enrich --cnj 0000001-02.2024.8.22.0001 --skip-upload
    uv run datajud enrich --cnj-file cnjs.txt

Upload requires ``IA_ACCESS_KEY`` / ``IA_SECRET_KEY`` in the environment::

    uv run --env-file ~/workspace/.env datajud enrich --tribunal tjro

Aggregate the acervo without downloading documents / show manifest state::

    uv run datajud facetas --tribunal tjro --por classe
    uv run datajud status

In CI, ``.github/workflows/datajud-enrich.yml`` runs the same commands with
secrets injected. It is ``workflow_dispatch`` only (no cron) — trigger it
manually from the Actions tab.
"""

from __future__ import annotations

import asyncio
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import httpx
import structlog
import typer
from pydantic import ValidationError

from datajud import archive
from datajud.client import DEFAULT_TRIBUNAL, FACET_FIELDS, DataJudClient, DataJudError
from datajud.dedup import capa_row_key, dedup_capas, merge_capa_rows, merge_movimento_rows
from datajud.manifest import STATUS_OK, ManifestDataJud
from datajud.models import ProcessoCapa, normalizar_cnj


log = structlog.get_logger()

app = typer.Typer(
    name="datajud",
    help="DataJud (CNJ) — enriquecimento de metadados processuais (capa + movimentos).",
    no_args_is_help=True,
)

_DEFAULT_DATA_DIR = Path("data/datajud")
_DEFAULT_SOURCES_DIR = Path("data")
_MANIFEST_NAME = "datajud-manifest.csv"

_UNIFICADOS_IA_URL = (
    "https://archive.org/download/causaganha-dashboard/processos_unificados.parquet"
)


def _manifest_path(data_dir: Path) -> Path:
    return data_dir / _MANIFEST_NAME


# ── CNJ sources ──────────────────────────────────────────────────────────


def _read_cnj_file(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _source_selects(sources_dir: Path) -> list[str]:
    selects: list[str] = []
    unificados = sources_dir / "processos_unificados.parquet"
    if unificados.exists():
        selects.append(f"SELECT nr_processo AS cnj FROM read_parquet('{unificados}')")
    juris_files = sorted(sources_dir.glob("tjro-juris/*/tjro-juris-*.parquet"))
    if juris_files:
        juris_list = ", ".join(f"'{p}'" for p in juris_files)
        selects.append(f"SELECT nr_processo AS cnj FROM read_parquet([{juris_list}])")
    stj = sources_dir / "stj" / "stj-acordaos.parquet"
    if stj.exists():
        selects.append(f"SELECT \"numeroProcesso\" AS cnj FROM read_parquet('{stj}')")
    return selects


def _try_download_unificados(sources_dir: Path) -> None:
    """Best-effort download of processos_unificados from IA (CI cold start)."""
    dest = sources_dir / "processos_unificados.parquet"
    typer.echo(f"No local sources — trying {_UNIFICADOS_IA_URL}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(_UNIFICADOS_IA_URL, timeout=180) as resp:  # noqa: S310 — fixed archive.org URL
            dest.write_bytes(resp.read())
    except OSError as exc:
        typer.echo(f"  WARNING: could not download processos_unificados — {exc}", err=True)


def _collect_source_cnjs(sources_dir: Path) -> list[str]:
    """Distinct valid CNJs from the local source parquets (RFC 0010 §2)."""
    import duckdb

    selects = _source_selects(sources_dir)
    if not selects:
        _try_download_unificados(sources_dir)
        selects = _source_selects(sources_dir)
    if not selects:
        return []
    union = " UNION ALL ".join(selects)
    sql = (
        "SELECT DISTINCT regexp_replace(cnj, '[^0-9]', '', 'g') AS cnj "
        f"FROM ({union}) "
        "WHERE length(regexp_replace(cnj, '[^0-9]', '', 'g')) = 20 ORDER BY cnj"
    )
    con = duckdb.connect()
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def _gather_cnjs(cnj: list[str] | None, cnj_file: Path | None, sources_dir: Path) -> list[str]:
    explicit: list[str] = list(cnj or [])
    if cnj_file is not None:
        explicit.extend(_read_cnj_file(cnj_file))
    if explicit:
        return explicit
    return _collect_source_cnjs(sources_dir)


# ── Parquet round-trip ───────────────────────────────────────────────────


def _read_parquet_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    import duckdb

    con = duckdb.connect()
    try:
        cursor = con.execute(f"SELECT * FROM read_parquet('{path}')")
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    finally:
        con.close()


# ── Fetch ────────────────────────────────────────────────────────────────


async def _fetch_capas(cnjs: list[str], tribunal: str, batch_size: int) -> list[ProcessoCapa]:
    async with DataJudClient(tribunal=tribunal, batch_size=batch_size) as client:
        sources = await client.fetch_processos(cnjs)
    capas: list[ProcessoCapa] = []
    for source in sources:
        try:
            capas.append(ProcessoCapa.from_source(source))
        except ValidationError as exc:
            log.warning(
                "datajud_malformed_document",
                error=str(exc),
                numero_processo=source.get("numeroProcesso"),
            )
    return capas


def _persist(
    capas: list[ProcessoCapa],
    tribunal: str,
    data_dir: Path,
) -> tuple[Path, Path, int, int]:
    """Merge fresh capas into the tribunal parquets. Returns paths + counts."""
    consultado_em = datetime.now(UTC).isoformat(timespec="seconds")
    new_capa_rows = [c.capa_row(tribunal=tribunal, consultado_em=consultado_em) for c in capas]
    new_mov_rows = [row for c in capas for row in c.movimento_rows(tribunal=tribunal)]
    refreshed_keys = {capa_row_key(row) for row in new_capa_rows}

    capa_path = data_dir / archive.capa_parquet_name(tribunal)
    mov_path = data_dir / archive.movimentos_parquet_name(tribunal)
    capa_rows = merge_capa_rows(_read_parquet_rows(capa_path), new_capa_rows)
    mov_rows = merge_movimento_rows(_read_parquet_rows(mov_path), new_mov_rows, refreshed_keys)

    n_capa = archive.write_capa_parquet(capa_rows, capa_path)
    n_mov = archive.write_movimentos_parquet(mov_rows, mov_path)
    return capa_path, mov_path, n_capa, n_mov


def _upload(paths: list[Path], tribunal: str, ia_key: str, ia_secret: str) -> None:
    if not ia_key or not ia_secret:
        typer.echo("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", err=True)
        raise typer.Exit(1)
    for path in paths:
        typer.echo(f"Uploading {path.name} to IA item {archive.item_id(tribunal)} …")
        if not archive.upload_parquet(path, tribunal, ia_key, ia_secret):
            typer.echo(f"Upload FAILED: {path.name}", err=True)
            raise typer.Exit(1)
    typer.echo("Upload complete.")


# ── Commands ─────────────────────────────────────────────────────────────


@app.command()
def enrich(
    tribunal: Annotated[str, typer.Option(help="Sigla do índice DataJud (ex.: tjro, stj).")] = (
        DEFAULT_TRIBUNAL
    ),
    data_dir: Annotated[Path, typer.Option(help="Diretório dos parquets/manifest DataJud.")] = (
        _DEFAULT_DATA_DIR
    ),
    sources_dir: Annotated[
        Path, typer.Option(help="Diretório com os parquets-fonte de CNJs (data/).")
    ] = _DEFAULT_SOURCES_DIR,
    cnj: Annotated[
        list[str] | None, typer.Option("--cnj", help="CNJ explícito (repetível).")
    ] = None,
    cnj_file: Annotated[Path | None, typer.Option(help="Arquivo com um CNJ por linha.")] = None,
    limit: Annotated[int, typer.Option(help="Máximo de CNJs a consultar (0 = sem limite).")] = 0,
    max_age_days: Annotated[
        int, typer.Option(help="Janela de frescor: reconsulta CNJs mais velhos que N dias.")
    ] = 30,
    batch_size: Annotated[int, typer.Option(help="CNJs por requisição (terms).")] = 50,
    skip_upload: Annotated[
        bool, typer.Option("--skip-upload", help="Não envia os parquets ao IA.")
    ] = False,
    ia_key: Annotated[str, typer.Option(envvar="IA_ACCESS_KEY", help="IA S3 access key.")] = "",
    ia_secret: Annotated[str, typer.Option(envvar="IA_SECRET_KEY", help="IA S3 secret key.")] = "",
) -> None:
    """Consulta capa + movimentos dos CNJs conhecidos e arquiva parquets no IA."""
    candidates = _gather_cnjs(cnj, cnj_file, sources_dir)
    if not candidates:
        typer.echo("No CNJs found (no local source parquets and no --cnj/--cnj-file).", err=True)
        raise typer.Exit(1)

    manifest = ManifestDataJud.load_local(_manifest_path(data_dir))
    pending: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        norm = normalizar_cnj(raw)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if manifest.needs_refresh(norm, tribunal, max_age_days=max_age_days):
            pending.append(norm)
    if limit > 0:
        pending = pending[:limit]

    if not pending:
        typer.echo("Nothing to do — all CNJs are fresh in the manifest.")
        return

    typer.echo(f"Consulting {len(pending)} CNJ(s) on {tribunal.upper()} …")
    try:
        capas = dedup_capas(asyncio.run(_fetch_capas(pending, tribunal, batch_size)))
    except (DataJudError, httpx.HTTPError) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(1) from exc

    capa_path, mov_path, n_capa, n_mov = _persist(capas, tribunal, data_dir)
    typer.echo(f"  {n_capa:,} capa rows → {capa_path}")
    typer.echo(f"  {n_mov:,} movimento rows → {mov_path}")

    # Mark the manifest fresh only after a successful upload (or an explicit
    # --skip-upload) — otherwise a failed IA push would be indistinguishable
    # from a completed one, and needs_refresh() would skip these CNJs for up
    # to max_age_days before the upload is ever retried.
    if skip_upload:
        typer.echo("Skipping IA upload (--skip-upload).")
    else:
        _upload([capa_path, mov_path], tribunal, ia_key, ia_secret)

    found = Counter(capa.cnj for capa in capas)
    for consulted in pending:
        manifest.upsert(consulted, tribunal, docs=found.get(consulted, 0), status=STATUS_OK)
    manifest.save_local(_manifest_path(data_dir))
    typer.echo(f"Manifest saved ({len(manifest)} entries).")


@app.command()
def facetas(
    tribunal: Annotated[str, typer.Option(help="Sigla do índice DataJud.")] = DEFAULT_TRIBUNAL,
    por: Annotated[
        str, typer.Option(help=f"Dimensão da agregação: {', '.join(FACET_FIELDS)}.")
    ] = "classe",
    limite: Annotated[int, typer.Option(help="Número de buckets.")] = 15,
) -> None:
    """Agrega o acervo por classe/assunto/órgão/grau/sistema (sem baixar docs)."""
    if por not in FACET_FIELDS:
        typer.echo(f"ERROR: --por must be one of: {', '.join(FACET_FIELDS)}.", err=True)
        raise typer.Exit(2)

    async def _run() -> tuple[int, list[dict]]:
        async with DataJudClient(tribunal=tribunal) as client:
            return await client.facetas(por, limite=limite)

    try:
        total, buckets = asyncio.run(_run())
    except (DataJudError, httpx.HTTPError) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Panorama por {por} — {tribunal.upper()} (total no acervo: {total:,})")
    for bucket in buckets:
        typer.echo(f"  {bucket['qtd']:>9,}  {bucket['chave']}")
    if not buckets:
        typer.echo("  (nenhum bucket)")


@app.command()
def status(
    data_dir: Annotated[Path, typer.Option(help="Diretório dos parquets/manifest DataJud.")] = (
        _DEFAULT_DATA_DIR
    ),
) -> None:
    """Mostra o estado do manifest DataJud."""
    manifest = ManifestDataJud.load_local(_manifest_path(data_dir))
    entries = manifest.all_entries()
    if not entries:
        typer.echo("Manifest is empty or not found.")
        return
    ok = sum(1 for e in entries if e.status == STATUS_OK)
    com_docs = sum(1 for e in entries if e.status == STATUS_OK and e.docs > 0)
    typer.echo(f"DataJud manifest: {_manifest_path(data_dir)}")
    typer.echo(f"  CNJs consultados : {len(entries)}")
    typer.echo(f"  Status ok        : {ok}")
    typer.echo(f"  Com documentos   : {com_docs}")
    typer.echo(f"  Sem documentos   : {ok - com_docs}")
    typer.echo(f"  Com erro         : {len(entries) - ok}")


if __name__ == "__main__":
    app()
