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
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from datajud import backlog as backlog_engine
from datajud import cdc as cdc_engine
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


@app.command(name="cdc")
def cdc_cmd(
    *,
    tribunal: Annotated[
        str, Parameter(help="Sigla do índice DataJud (ex.: tjro, tjce, tjsp).")
    ] = DEFAULT_TRIBUNAL,
    since: Annotated[
        str | None,
        Parameter(name="--since", help="Data/hora inicial ISO (ex.: 2026-01-01T00:00:00.000Z)."),
    ] = None,
    until: Annotated[
        str | None,
        Parameter(name="--until", help="Data/hora final ISO (ex.: 2026-03-01T00:00:00.000Z)."),
    ] = None,
    page_size: Annotated[
        int, Parameter(help="Tamanho do lote por página search_after (padrão 1000).")
    ] = 1000,
    max_pages: Annotated[
        int | None, Parameter(help="Limite máximo de páginas a extrair nesta sessão.")
    ] = None,
    no_resume: Annotated[
        bool,
        Parameter(name="--no-resume", negative=[], help="Ignora checkpoint e inicia do zero."),
    ] = False,
    skip_consolidate: Annotated[
        bool,
        Parameter(
            name="--skip-consolidate",
            negative=[],
            help="Não consolida deltas L1 em parquets L0 ao final.",
        ),
    ] = False,
    no_pack_daily: Annotated[
        bool,
        Parameter(
            name="--no-pack-daily",
            negative=[],
            help="Não gera o arquivo ZIP diário com processos completos.",
        ),
    ] = False,
    upload: Annotated[
        bool,
        Parameter(
            name="--upload",
            negative=[],
            help="Envia os artefatos diários e canônicos para o Internet Archive.",
        ),
    ] = False,
    skip_upload: Annotated[
        bool,
        Parameter(
            name="--skip-upload",
            negative=[],
            help="Ignora envio ao Internet Archive.",
        ),
    ] = False,
    data_dir: Annotated[
        Path, Parameter(help="Diretório base do CDC (checkpoints e deltas).")
    ] = cdc_engine.DEFAULT_CDC_DIR,
    canonical_dir: Annotated[
        Path, Parameter(help="Diretório dos parquets canônicos L0.")
    ] = cdc_engine.DEFAULT_CANONICAL_DIR,
) -> int:
    """Extração incremental de processos via CDC search_after com deltas particionados."""
    ia_key, ia_secret = service.ia_credentials()
    should_upload = upload and not skip_upload

    print(f"DataJud CDC — Tribunal: {tribunal.upper()}")
    if since:
        print(f"  Filtro since  : {since}")
    if until:
        print(f"  Filtro until  : {until}")
    print(f"  Page size     : {page_size:,}")
    print(f"  Base dir      : {data_dir}")
    print(f"  Pack Daily    : {not no_pack_daily}")
    print(f"  Upload IA     : {should_upload}")

    try:
        res = asyncio.run(
            cdc_engine.sync_tribunal_cdc(
                tribunal,
                since_iso=since,
                until_iso=until,
                page_size=page_size,
                max_pages=max_pages,
                resume=not no_resume,
                consolidate=not skip_consolidate,
                pack_daily=not no_pack_daily,
                upload=should_upload,
                base_dir=data_dir,
                canonical_dir=canonical_dir,
                ia_key=ia_key,
                ia_secret=ia_secret,
            )
        )
    except (DataJudError, httpx.HTTPError) as exc:
        print(f"ERROR no CDC: {exc}", file=sys.stderr)
        return 1

    print("\nSincronização CDC concluída:")
    print(f"  Documentos nesta sessão: {res.documents_streamed:,}")
    print(f"  Lotes (batches) salvos : {res.batches_streamed:,}")
    print(f"  Total acumulado        : {res.checkpoint.total_documents:,}")
    print(f"  Última atualização     : {res.checkpoint.last_updated_at or 'n/a'}")
    print(f"  Status do checkpoint   : {res.checkpoint.status}")

    if res.consolidated_capas is not None:
        print("\nConsolidação Canônica L0:")
        print(f"  Total de capas        : {res.consolidated_capas:,}")
        print(f"  Total de movimentos   : {res.consolidated_movs or 0:,}")

    if res.daily_zip_path:
        print("\nPacote Diário ZIP (Internet Archive Transparent Unzip):")
        print(f"  Arquivo gerado        : {res.daily_zip_path.name}")
        print(f"  Processos empacotados : {res.daily_processes_count:,}")
        print(f"  Total indexado        : {res.index_total:,}")

    if res.uploaded_files:
        print(f"\nUpload IA concluído ({len(res.uploaded_files)} arquivos):")
        for uf in res.uploaded_files:
            print(f"  ✓ {uf}")

    return 0


@app.command(name="backlog")
def backlog_cmd(
    *,
    tribunal: Annotated[
        str, Parameter(help="Sigla do índice DataJud (ex.: tjro, tjce, tjsp).")
    ] = DEFAULT_TRIBUNAL,
    start_year: Annotated[int, Parameter(help="Ano inicial do backlog.")] = 2024,
    end_year: Annotated[int, Parameter(help="Ano final do backlog.")] = 2026,
    slice_by: Annotated[
        str,
        Parameter(help="Fatiamento temporal: 'day' (diário), 'month' (mensal) ou 'year' (anual)."),
    ] = "day",
    max_slices: Annotated[
        int | None, Parameter(help="Máximo de fatias a processar nesta sessão.")
    ] = None,
    page_size: Annotated[int, Parameter(help="Tamanho do lote por página search_after.")] = 1000,
    upload: Annotated[
        bool,
        Parameter(name="--upload", negative=[], help="Envia parquets ao Internet Archive."),
    ] = False,
    status: Annotated[
        bool,
        Parameter(name="--status", negative=[], help="Mostra o panorama de fatias do backlog."),
    ] = False,
    data_dir: Annotated[
        Path, Parameter(help="Diretório base do backlog.")
    ] = backlog_engine.DEFAULT_BACKLOG_DIR,
) -> int:
    """Coleta e ingestão de backlog histórico particionado em fatias temporais."""
    store = backlog_engine.DataJudBacklogStore(data_dir / "backlog_slices.sqlite")
    console = Console()

    if status:
        slices = store.list_slices(tribunal)
        if not slices:
            console.print(
                f"[yellow]Nenhum backlog registrado para {tribunal.upper()} em {data_dir}.[/yellow]"
            )
            return 0

        table = Table(title=f"Status do Backlog — {tribunal.upper()} ({len(slices)} fatias)")
        table.add_column("Status", style="bold")
        table.add_column("Fatias", justify="right")
        table.add_column("Processos Coletados", justify="right", style="green")

        by_status: dict[str, list[backlog_engine.BacklogSlice]] = {}
        for s in slices:
            by_status.setdefault(s.status, []).append(s)

        for st, items in sorted(by_status.items()):
            docs = sum(item.documentos_coletados for item in items)
            color = (
                "green"
                if st == "completed"
                else ("yellow" if st == "in_progress" else ("red" if st == "error" else "cyan"))
            )
            table.add_row(f"[{color}]{st.capitalize()}[/{color}]", str(len(items)), f"{docs:,}")

        console.print(table)
        total_docs = sum(s.documentos_coletados for s in slices)
        console.print(
            f"[bold]Total acumulado:[/bold] [green]{total_docs:,}[/green] processos coletados."
        )
        return 0

    ia_key, ia_secret = service.ia_credentials()
    console.print(f"[bold cyan]DataJud Backlog — Tribunal: {tribunal.upper()}[/bold cyan]")
    console.print(f"  Período       : {start_year} a {end_year} (fatiamento: {slice_by})")
    console.print(f"  Page size     : {page_size:,}")
    console.print(f"  Upload IA     : {upload}")

    # Discover target slices count for the progress bar
    store.init_slices(tribunal.lower(), start_year, end_year, slice_by=slice_by)
    all_slices = store.list_slices(tribunal.lower())
    pending_count = sum(1 for s in all_slices if s.status in ("pending", "in_progress"))
    target_count = min(pending_count, max_slices) if max_slices is not None else pending_count

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=35),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        TextColumn("[green]• {task.fields[docs]} docs[/green]"),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            f"Backlog {tribunal.upper()}",
            total=target_count,
            docs=0,
        )

        def _on_start(s: backlog_engine.BacklogSlice) -> None:
            if s.dia:
                date_str = f"{s.ano}-{s.mes:02d}-{s.dia:02d}"
            elif s.mes:
                date_str = f"{s.ano}-{s.mes:02d}"
            else:
                date_str = f"{s.ano}"
            progress.update(task_id, description=f"Backlog {tribunal.upper()} [{date_str}]")

        total_accum_docs = 0

        def _on_done(s: backlog_engine.BacklogSlice, docs: int) -> None:
            nonlocal total_accum_docs
            total_accum_docs += docs
            progress.update(task_id, advance=1, docs=total_accum_docs)

        try:
            res = asyncio.run(
                backlog_engine.run_backlog(
                    tribunal,
                    start_year,
                    end_year,
                    slice_by=slice_by,
                    max_slices=max_slices,
                    page_size=page_size,
                    upload=upload,
                    base_dir=data_dir,
                    ia_key=ia_key,
                    ia_secret=ia_secret,
                    on_slice_start=_on_start,
                    on_slice_done=_on_done,
                )
            )
        except (DataJudError, httpx.HTTPError) as exc:
            console.print(f"[bold red]ERROR no Backlog:[/bold red] {exc}", file=sys.stderr)
            return 1

    console.print("\n[bold green]Sessão de Backlog concluída:[/bold green]")
    console.print(f"  Fatias processadas nesta sessão: {res['slices_processed']}")
    console.print(f"  Documentos coletados           : {res['total_documents']:,}")

    return 0


if __name__ == "__main__":
    app()
