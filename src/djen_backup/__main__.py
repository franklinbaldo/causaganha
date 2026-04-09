#!/usr/bin/env python
"""Premium CLI entry point for ``djen-backup``."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Optional

import structlog
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typer import Option, Argument

from djen_backup.backfill import (
    BackfillConfig,
    load_backfill_state,
    run_backfill,
    save_backfill_state,
)
from djen_backup.credentials import get_ia_s3_auth

console = Console()
app = typer.Typer(
    name="djen-backup",
    help="🚀 Engine de Backfill do CausaGanha — Download histórico de Cadernos DJEN",
    rich_markup_mode="rich",
    add_completion=True,
    pretty_exceptions_show_locals=False,
)


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _resolve_proxy_url() -> str:
    return (
        os.environ.get("DJEN_PROXY_URL", "").strip() or "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
    )


def _resolve_ia_auth(*, dry_run: bool) -> str:
    try:
        # Priority: Env -> Prompt if missing
        auth = get_ia_s3_auth()
        return auth
    except RuntimeError as exc:
        if dry_run:
            return "LOW dry-run:dry-run"
        
        console.print(f"[bold red]Credenciais IA não encontradas:[/] {exc}")
        auth = typer.prompt(
            "Digite seu Access Key e Secret Key (formato access:secret)",
            hide_input=True,
        )
        if not auth or ":" not in auth:
            console.print("[bold red]Erro:[/] Formato inválido. Use access_key:secret_key")
            raise typer.Exit(code=1)
        return auth


@app.command()
def run(
    start_date: Annotated[
        Optional[str], 
        Option("--start", "-s", help="Data mais recente para começar o backfill (YYYY-MM-DD). Default: ontem.")
    ] = None,
    end_date: Annotated[
        Optional[str], 
        Option("--end", "-e", help="Data mínima para o backfill (YYYY-MM-DD). Default: sem limite.")
    ] = None,
    tribunal: Annotated[
        Optional[str], 
        Option("--tribunal", "-t", help="Processar apenas um tribunal específico (ex: tjsp).")
    ] = None,
    workers: Annotated[
        int, 
        Option("--workers", "-w", help="Número de workers paralelos.")
    ] = 1,
    deadline_minutes: Annotated[
         int, 
         Option("--deadline", "-d", help="Tempo máximo de execução em minutos.")
    ] = 45,
    max_items: Annotated[
        int, 
        Option("--max-items", "-m", help="Número máximo de datas por tribunal por execução.")
    ] = 0,
    backfill_state_file: Annotated[
        Path, 
        Option("--backfill-state", help="Caminho do arquivo de progresso (JSON).")
    ] = Path("data/backfill-state.json"),
    state_file: Annotated[
        Path, 
        Option("--state", help="Caminho do cache de estado IA (JSON).")
    ] = Path("data/ia-state.json"),
    dry_run: Annotated[
        bool, 
        Option("--dry-run", help="Logar ações sem fazer upload real.")
    ] = False,
    skip_absent: Annotated[
        bool, 
        Option("--skip-absent", help="Não enviar marcadores de 'ausente' para o IA.")
    ] = False,
    publish: Annotated[
        bool, 
        Option("--publish", help="Publicar status ao vivo no ntfy.")
    ] = False,
    mostly_complete: Annotated[
        bool, 
        Option("--skip-mostly-complete", help="Pular se o dia já tiver > 80% de coleta.")
    ] = False,
    rich_ui: Annotated[
        bool, 
        Option("--rich/--no-rich", help="Ativar/desativar interface rica com Painel Live.")
    ] = True,
) -> None:
    """🚀 Executa a engine de backup para coletar cadernos do DJEN."""
    
    today = datetime.now(tz=UTC).date()
    resolved_end = _parse_date(start_date) if start_date else today - timedelta(days=1)
    resolved_start = _parse_date(end_date) if end_date else None

    # Ensure directories exist
    backfill_state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    config = BackfillConfig(
        start_date=resolved_end,
        lower_bound=resolved_start,
        tribunal=tribunal,
        deadline_minutes=deadline_minutes,
        max_items=max_items,
        workers=workers,
        backfill_state_file=backfill_state_file,
        state_file=state_file,
        djen_proxy_url=_resolve_proxy_url(),
        ia_auth=_resolve_ia_auth(dry_run=dry_run),
        dry_run=dry_run,
        skip_absent_markers=skip_absent,
        publish_live_status=publish,
        skip_if_mostly_complete=mostly_complete,
        use_rich=rich_ui,
    )

    console.print(
        Panel(
            f"🚀 [bold blue]Iniciando Backfill DJEN[/bold blue]\n\n"
            f"📅 Período: [cyan]{resolved_end}[/] → [cyan]{resolved_start or '∞'}[/]\n"
            f"⚖️ Tribunal: [bold magenta]{(tribunal or 'TODOS').upper()}[/bold magenta]\n"
            f"🧵 Workers: [bold]{workers}[/] | ⏱ Deadline: [bold]{deadline_minutes} min[/]\n"
            f"🧪 Mode: [bold yellow]{'DRY RUN' if dry_run else 'PRODUCTION'}[/bold yellow]",
            title="Djen Backup Configuration",
            border_style="blue",
        )
    )

    exit_code = asyncio.run(run_backfill(config))
    
    if exit_code == 0:
        console.print("\n[bold green]✨ Backfill concluído com sucesso![/]")
    else:
        console.print("\n[bold red]❌ Backfill finalizado com erros.[/]")
        raise typer.Exit(code=exit_code)


@app.command()
def status(
    backfill_state_file: Annotated[
        Path, 
        Option("--backfill-state", help="Caminho do arquivo de progresso (JSON).")
    ] = Path("data/backfill-state.json"),
) -> None:
    """📊 Mostra o status atual do progresso por tribunal."""
    bstate = load_backfill_state(backfill_state_file)
    progress = bstate.get_all_progress()

    if not progress:
        console.print("[yellow]Nenhum estado de backfill encontrado.[/yellow]")
        return

    running = sum(1 for p in progress.values() if not p.stopped)
    stopped = sum(1 for p in progress.values() if p.stopped)

    console.print(
        Panel(
            f"Tribunais: [bold blue]{len(progress)}[/bold blue] total | "
            f"[bold green]{running}[/bold green] ativos | "
            f"[bold red]{stopped}[/bold red] finalizados",
            title="Resumo do Progresso",
            expand=False,
            border_style="magenta"
        )
    )

    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Tribunal", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("Cursor", justify="center")
    table.add_column("Streak", justify="right")
    table.add_column("Último Sucesso", justify="center")
    table.add_column("Resultado", justify="center")

    for code in sorted(progress):
        prog = progress[code]
        status_style = "bold red" if prog.stopped else "bold green"
        status_text = "PARADO" if prog.stopped else "ativo"

        last_result = prog.last_result or "-"
        result_style = "dim"
        if last_result == "hit":
            result_style = "bold green"
        elif last_result == "empty":
            result_style = "yellow"
        elif last_result == "error":
            result_style = "bold red"

        hit_str = prog.last_hit_date.isoformat() if prog.last_hit_date else "nunca"

        table.add_row(
            code.upper(),
            f"[{status_style}]{status_text}[/{status_style}]",
            prog.cursor_date.isoformat(),
            str(prog.empty_streak),
            hit_str,
            f"[{result_style}]{last_result}[/{result_style}]",
        )

    console.print(table)


@app.command()
def reset(
    tribunal: Annotated[Optional[str], Argument(help="Código do tribunal (ex: tjsp) ou deixe vazio para --all")] = None,
    all: Annotated[bool, Option("--all", help="Resetar TODOS os tribunais parados")] = False,
    backfill_state_file: Annotated[
        Path, 
        Option("--backfill-state", help="Caminho do arquivo de progresso (JSON).")
    ] = Path("data/backfill-state.json"),
    set_cursor: Annotated[
        Optional[str], 
        Option("--set-cursor", help="Define o cursor para uma data específica (YYYY-MM-DD).")
    ] = None,
) -> None:
    """🔄 Destrava tribunais parados para permitir nova varredura."""
    if not tribunal and not all:
        console.print("[bold red]Erro:[/] Forneça o código do tribunal ou use --all")
        raise typer.Exit(1)

    bstate = load_backfill_state(backfill_state_file)
    
    async def _reset() -> int:
        count = 0
        target_cursor = date.fromisoformat(set_cursor) if set_cursor else None

        if tribunal:
            if target_cursor:
                if await bstate.set_cursor(tribunal, target_cursor):
                    console.print(f"✅ Reset: [bold]{tribunal}[/] cursor definido para [cyan]{target_cursor}[/]")
                    count = 1
                else:
                    console.print(f"[bold red]Erro:[/] Tribunal {tribunal} não encontrado.", style="red")
            elif await bstate.reset_tribunal(tribunal):
                console.print(f"✅ Reset: [bold]{tribunal}[/] destravado.")
                count = 1
        else:
            progress = bstate.get_all_progress()
            for code, prog in progress.items():
                if prog.stopped:
                    await bstate.reset_tribunal(code)
                    console.print(f"✅ Reset: [bold]{code}[/] destravado.")
                    count += 1
        return count

    count = asyncio.run(_reset())
    if count > 0:
        save_backfill_state(bstate, backfill_state_file)
        console.print(f"\n[bold green]{count}[/] tribunal(s) resetado(s).")
    else:
        console.print("[yellow]Nada para resetar.[/yellow]")


def main() -> None:
    """Python entry point."""
    app()


if __name__ == "__main__":
    main()
