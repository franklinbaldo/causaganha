"""TJRO JURIS CLI — crawl, upload, status, consolidate.

Manual execution
----------------
Crawl JURIS into monthly parquets (optionally windowed by year/month and tipo)::

    uv run tjro-juris crawl data/tjro-juris --ano 2024 --tipo "ACÓRDÃO" --tipo "SENTENÇA"
    uv run tjro-juris crawl data/tjro-juris --mes 2026-07   # incremental (current month)

Upload pending parquets to the yearly ``tjro-juris-{year}`` IA items
(requires ``IAS3_ACCESS_KEY`` / ``IAS3_SECRET_KEY`` in the environment)::

    uv run --env-file ~/workspace/.env tjro-juris upload data/tjro-juris

Show manifest status / consolidate a year into a single deduplicated parquet::

    uv run tjro-juris status data/tjro-juris
    uv run tjro-juris consolidate data/tjro-juris 2024

When no local manifest exists, ``crawl``/``upload`` first try to restore it
from the public IA item (``tjro-juris``); ``upload`` pushes it back so
scheduled runs on blank runners stay incremental.

In CI, ``.github/workflows/tjro-sync.yml`` runs the same commands daily
(scheduled runs continue the historical backfill via ``--desde-ano 1988``,
not just the current month) plus ``workflow_dispatch`` for ad-hoc
``--ano``/``--mes``/``--desde-ano`` runs.

Business logic lives in ``tjro_juris.service`` (RFC 0013 Fase 2); this
module only parses argv and echoes results.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from tjro_juris import service


app = typer.Typer(name="tjro-juris", help="TJRO JURIS scraping and archival.")


@app.command()
def crawl(
    data_dir: Annotated[Path, typer.Argument(help="Directory to store parquet files")],
    tipo: Annotated[
        list[str] | None, typer.Option("--tipo", "-t", help="Filter to these tipos")
    ] = None,
    ano: Annotated[int | None, typer.Option("--ano", "-a", help="Only crawl this year")] = None,
    mes: Annotated[
        str | None,
        typer.Option(
            "--mes",
            "-m",
            help="Only crawl this month (AAAA-MM) — incremental mode for scheduled runs",
        ),
    ] = None,
    desde_ano: Annotated[
        int | None,
        typer.Option(
            "--desde-ano",
            help=(
                f"Full backfill starting from this year instead of the default "
                f"({service.DEFAULT_START_YEAR}). Mutually exclusive with --ano/--mes."
            ),
        ),
    ] = None,
) -> None:
    """Crawl JURIS and save as parquet files per (tipo, mes_ano). See ``service.crawl_juris``."""
    try:
        service.crawl_juris(data_dir, tipo, ano, mes, desde_ano)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def upload(
    data_dir: Annotated[Path, typer.Argument(help="Directory with parquet files")],
) -> None:
    """Upload parquets (and the manifest) to Internet Archive."""
    asyncio.run(service.upload_pending(data_dir))


@app.command()
def status(
    data_dir: Annotated[Path, typer.Argument(help="Directory with manifest")],
) -> None:
    """Show manifest status."""
    result = service.manifest_status(data_dir)
    typer.echo(f"Total entries: {result.total}")
    typer.echo(f"Uploaded:      {result.uploaded}")
    typer.echo(f"Pending:       {result.pending}")


@app.command()
def consolidate(
    data_dir: Annotated[Path, typer.Argument(help="Directory with parquet files")],
    year: Annotated[int, typer.Argument(help="Year to consolidate")],
) -> None:
    """Consolidate monthly parquets for a year into a single deduplicated file."""
    output, count = service.consolidate_parquets(data_dir, year)
    typer.echo(f"Consolidated {count} documents to {output}")


if __name__ == "__main__":
    app()
