"""DataJud CLI — enrich, facetas, status.

Manual execution
----------------
Enrich known CNJs with official capa + movimentos (CNJs come from local
source parquets — indice_processual, TJRO JURIS, STJ — or explicitly)::

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
import sys
from pathlib import Path
from typing import Annotated

import httpx
from cyclopts import App, Parameter

from datajud import service
from datajud.client import DEFAULT_TRIBUNAL, FACET_FIELDS, DataJudError


app = App(
    name="datajud",
    help="DataJud (CNJ) — enriquecimento de metadados processuais (capa + movimentos).",
    # Cyclopts registers --version by default; the original Typer app never
    # declared it, so leaving it on would silently accept a form that used
    # to be a usage error (RFC 0013 Fase 4 review, #855 round 3).
    version_flags=[],
)


@app.default
def _no_command() -> int:
    """Show help and exit 2 on a bare invocation (no subcommand).

    The original Typer app set ``no_args_is_help=True``, which shows help
    and exits 2 (Click's convention for incomplete usage) — distinct from
    the 3 documented parse-error cases (RFC 0013 Fase 4) that changed from
    Click's 2 to Cyclopts' own 1. Cyclopts has no built-in equivalent to
    `no_args_is_help`; without this, a bare ``datajud`` would print help and
    exit 0, silently dropping the "incomplete usage" signal for scripts.
    """
    app.help_print([])
    return 2


@app.command
def enrich(
    *,
    tribunal: Annotated[str, Parameter(help="Sigla do índice DataJud (ex.: tjro, stj).")] = (
        DEFAULT_TRIBUNAL
    ),
    data_dir: Annotated[Path, Parameter(help="Diretório dos parquets/manifest DataJud.")] = (
        service.DEFAULT_DATA_DIR
    ),
    sources_dir: Annotated[
        Path, Parameter(help="Diretório com os parquets-fonte de CNJs (data/).")
    ] = service.DEFAULT_SOURCES_DIR,
    cnj: Annotated[
        list[str] | None, Parameter(name="--cnj", help="CNJ explícito (repetível).")
    ] = None,
    cnj_file: Annotated[Path | None, Parameter(help="Arquivo com um CNJ por linha.")] = None,
    limit: Annotated[int, Parameter(help="Máximo de CNJs a consultar (0 = sem limite).")] = 0,
    max_age_days: Annotated[
        int, Parameter(help="Janela de frescor: reconsulta CNJs mais velhos que N dias.")
    ] = 30,
    batch_size: Annotated[int, Parameter(help="CNJs por requisição (terms).")] = 50,
    skip_upload: Annotated[
        bool,
        Parameter(name="--skip-upload", negative=[], help="Não envia os parquets ao IA."),
    ] = False,
) -> int:
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
        print(
            "No CNJs found (no local source parquets and no --cnj/--cnj-file).",
            file=sys.stderr,
        )
        return 1
    if result.status == "nothing_to_do":
        print("Nothing to do — all CNJs are fresh in the manifest.")
        return 0
    if result.status == "restore_error":
        print(f"State restore FAILED: {result.error}", file=sys.stderr)
        return 1
    if result.status == "fetch_error":
        print(f"ERROR: {result.error}", file=sys.stderr)
        return 1

    print(f"  {result.n_capa:,} capa rows → {result.capa_path}")
    print(f"  {result.n_mov:,} movimento rows → {result.mov_path}")

    if result.status == "missing_credentials":
        print("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", file=sys.stderr)
        return 1
    if result.status == "upload_error":
        print(f"Upload FAILED: {result.error}", file=sys.stderr)
        return 1

    if skip_upload:
        print("Skipping IA upload (--skip-upload).")
    else:
        print("Upload complete.")

    print(f"Manifest saved ({result.manifest_entries} entries).")
    return 0


@app.command
def facetas(
    *,
    tribunal: Annotated[str, Parameter(help="Sigla do índice DataJud.")] = DEFAULT_TRIBUNAL,
    por: Annotated[
        str, Parameter(help=f"Dimensão da agregação: {', '.join(FACET_FIELDS)}.")
    ] = "classe",
    limite: Annotated[int, Parameter(help="Número de buckets.")] = 15,
) -> int:
    """Agrega o acervo por classe/assunto/órgão/grau/sistema (sem baixar docs)."""
    if por not in FACET_FIELDS:
        print(f"ERROR: --por must be one of: {', '.join(FACET_FIELDS)}.", file=sys.stderr)
        return 2

    try:
        total, buckets = asyncio.run(service.facetas(tribunal, por, limite))
    except (DataJudError, httpx.HTTPError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Panorama por {por} — {tribunal.upper()} (total no acervo: {total:,})")
    for bucket in buckets:
        print(f"  {bucket['qtd']:>9,}  {bucket['chave']}")
    if not buckets:
        print("  (nenhum bucket)")
    return 0


@app.command
def status(
    *,
    data_dir: Annotated[Path, Parameter(help="Diretório dos parquets/manifest DataJud.")] = (
        service.DEFAULT_DATA_DIR
    ),
) -> None:
    """Mostra o estado do manifest DataJud."""
    result = service.manifest_status(data_dir)
    if result is None:
        print("Manifest is empty or not found.")
        return
    print(f"DataJud manifest: {service.manifest_path(data_dir)}")
    print(f"  CNJs consultados : {result.total}")
    print(f"  Status ok        : {result.ok}")
    print(f"  Com documentos   : {result.com_docs}")
    print(f"  Sem documentos   : {result.sem_docs}")
    print(f"  Com erro         : {result.com_erro}")


if __name__ == "__main__":
    app()
