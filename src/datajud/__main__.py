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
secrets injected, daily (``--tribunal tjro --limit 500``) plus
``workflow_dispatch`` for ad-hoc runs with different inputs.

Business logic lives in ``datajud.service`` (RFC 0013 Fase 2); this module
only parses argv and echoes results. ``IA_ACCESS_KEY``/``IA_SECRET_KEY`` are
read from the environment only — not CLI options — so they never appear in
``--help`` or in a future MCP tool's schema.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import httpx
import typer

from datajud import service
from datajud.client import DEFAULT_TRIBUNAL, FACET_FIELDS, DataJudError


app = typer.Typer(
    name="datajud",
    help="DataJud (CNJ) — enriquecimento de metadados processuais (capa + movimentos).",
    no_args_is_help=True,
)


@app.command()
def enrich(
    tribunal: Annotated[str, typer.Option(help="Sigla do índice DataJud (ex.: tjro, stj).")] = (
        DEFAULT_TRIBUNAL
    ),
    data_dir: Annotated[Path, typer.Option(help="Diretório dos parquets/manifest DataJud.")] = (
        service.DEFAULT_DATA_DIR
    ),
    sources_dir: Annotated[
        Path, typer.Option(help="Diretório com os parquets-fonte de CNJs (data/).")
    ] = service.DEFAULT_SOURCES_DIR,
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
) -> None:
    """Consulta capa + movimentos dos CNJs conhecidos e arquiva parquets no IA."""
    ia_key, ia_secret = service.ia_credentials()
    result = service.enrich(
        tribunal,
        data_dir,
        sources_dir,
        cnj,
        cnj_file,
        limit,
        max_age_days,
        batch_size,
        skip_upload=skip_upload,
        ia_key=ia_key,
        ia_secret=ia_secret,
    )

    if result.status == "no_cnjs":
        typer.echo("No CNJs found (no local source parquets and no --cnj/--cnj-file).", err=True)
        raise typer.Exit(1)
    if result.status == "nothing_to_do":
        typer.echo("Nothing to do — all CNJs are fresh in the manifest.")
        return
    if result.status == "fetch_error":
        typer.echo(f"ERROR: {result.error}", err=True)
        raise typer.Exit(1)

    typer.echo(f"  {result.n_capa:,} capa rows → {result.capa_path}")
    typer.echo(f"  {result.n_mov:,} movimento rows → {result.mov_path}")

    if result.status == "missing_credentials":
        typer.echo("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", err=True)
        raise typer.Exit(1)
    if result.status == "upload_error":
        typer.echo(f"Upload FAILED: {result.error}", err=True)
        raise typer.Exit(1)

    if skip_upload:
        typer.echo("Skipping IA upload (--skip-upload).")
    else:
        typer.echo("Upload complete.")

    typer.echo(f"Manifest saved ({result.manifest_entries} entries).")


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

    try:
        total, buckets = asyncio.run(service.facetas(tribunal, por, limite))
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
        service.DEFAULT_DATA_DIR
    ),
) -> None:
    """Mostra o estado do manifest DataJud."""
    result = service.manifest_status(data_dir)
    if result is None:
        typer.echo("Manifest is empty or not found.")
        return
    typer.echo(f"DataJud manifest: {service.manifest_path(data_dir)}")
    typer.echo(f"  CNJs consultados : {result.total}")
    typer.echo(f"  Status ok        : {result.ok}")
    typer.echo(f"  Com documentos   : {result.com_docs}")
    typer.echo(f"  Sem documentos   : {result.sem_docs}")
    typer.echo(f"  Com erro         : {result.com_erro}")


if __name__ == "__main__":
    app()
