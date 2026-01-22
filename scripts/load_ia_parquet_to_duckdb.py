#!/usr/bin/env python3
"""Load Internet Archive parquet files into DuckDB.

Joins comunicacoes with textos and loads into intimations table.

Usage:
    python scripts/load_ia_parquet_to_duckdb.py
    python scripts/load_ia_parquet_to_duckdb.py --parquet-dir data/ia_cache/djen-parquet-2026-01-21-TRF4
"""

from pathlib import Path

import duckdb
import structlog
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from causaganha.config import settings


logger = structlog.get_logger()
console = Console()
app = typer.Typer()


def load_ia_parquet_to_duckdb(
    parquet_dir: Path,
    db_path: Path,
) -> dict[str, int]:
    """Load IA parquet files into DuckDB.

    Args:
        parquet_dir: Directory containing comunicacoes.parquet and textos.parquet.
        db_path: Path to DuckDB database.

    Returns:
        Dict with counts of loaded records.
    """
    console.print(f"\n[cyan]Loading parquet files from {parquet_dir}...[/cyan]")

    comunicacoes_file = parquet_dir / "comunicacoes.parquet"
    textos_file = parquet_dir / "textos.parquet"

    if not comunicacoes_file.exists():
        console.print(f"[red]Error: {comunicacoes_file} not found[/red]")
        raise FileNotFoundError(f"comunicacoes.parquet not found in {parquet_dir}")

    if not textos_file.exists():
        console.print(f"[red]Error: {textos_file} not found[/red]")
        raise FileNotFoundError(f"textos.parquet not found in {parquet_dir}")

    # Connect to DuckDB
    conn = duckdb.connect(str(db_path))

    # Create schema if not exists
    schema_file = Path(__file__).parent.parent / "src/causaganha/v2/storage/schema.sql"
    if schema_file.exists():
        with schema_file.open() as f:
            schema_sql = f.read()
        conn.execute(schema_sql)
        logger.info("schema_initialized")

    console.print("  • Schema initialized")

    # Get counts before loading
    count_before = conn.execute("SELECT COUNT(*) FROM intimations").fetchone()[0]

    console.print(f"  • Current intimations count: {count_before}")

    # Join comunicacoes with textos and insert into intimations
    # Map columns from IA parquet to intimations schema
    console.print("  • Joining comunicacoes with textos and loading into intimations...")

    insert_sql = f"""
    INSERT OR IGNORE INTO intimations (
        id,
        numero_processo,
        data_disponibilizacao,
        sigla_tribunal,
        tipo_comunicacao,
        nome_orgao,
        texto,
        nome_classe,
        status,
        analyzed,
        created_at,
        updated_at
    )
    SELECT
        c.id,
        c.numero_processo,
        c.data_disponibilizacao::DATE,
        c.tribunal,
        c.tipo,
        c.orgao,
        t.texto,
        c.classe,
        c.status,
        FALSE as analyzed,
        NOW() as created_at,
        NOW() as updated_at
    FROM read_parquet('{comunicacoes_file}') c
    INNER JOIN read_parquet('{textos_file}') t ON c.texto_id = t.texto_id
    WHERE t.texto IS NOT NULL
      AND LENGTH(t.texto) > 100
    """

    try:
        conn.execute(insert_sql)
        console.print("  ✓ Data loaded successfully")
    except Exception as e:
        console.print(f"[red]Error loading data: {e}[/red]")
        logger.exception("failed_to_load_parquet", error=str(e))
        raise

    # Get counts after loading
    count_after = conn.execute("SELECT COUNT(*) FROM intimations").fetchone()[0]
    loaded_count = count_after - count_before

    # Get tribunal distribution
    tribunal_counts = conn.execute(
        """
        SELECT sigla_tribunal, COUNT(*) as count
        FROM intimations
        GROUP BY sigla_tribunal
        ORDER BY count DESC
        """
    ).fetchall()

    console.print(f"\n  ✓ Loaded {loaded_count} new intimations")
    console.print(f"  • Total intimations: {count_after}")
    console.print("\n  • Tribunal distribution:")
    for tribunal, count in tribunal_counts:
        console.print(f"    - {tribunal}: {count}")

    conn.close()

    return {
        "loaded": loaded_count,
        "total": count_after,
    }


@app.command()
def main(
    parquet_dir: str = typer.Option(
        "data/ia_cache/djen-parquet-2026-01-21-TRF4",
        "--parquet-dir",
        "-d",
        help="Directory containing comunicacoes.parquet and textos.parquet",
    ),
    db_path: str = typer.Option(
        str(settings.DATA_DIR / "causaganha_real.duckdb"),
        "--db",
        help="Path to DuckDB database",
    ),
) -> None:
    """Load IA parquet files into DuckDB database.

    Joins comunicacoes with textos and loads into intimations table.
    """
    console.print("[bold]Load IA Parquet to DuckDB[/bold]")
    console.print(f"Parquet directory: {parquet_dir}")
    console.print(f"Database: {db_path}\n")

    try:
        parquet_path = Path(parquet_dir)
        db_path_obj = Path(db_path)

        counts = load_ia_parquet_to_duckdb(parquet_path, db_path_obj)

        console.print("\n[bold green]✓ Load complete![/bold green]")
        console.print(f"\nDatabase: {db_path}")
        console.print(f"New intimations loaded: {counts['loaded']}")
        console.print(f"Total intimations: {counts['total']}")

        console.print("\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("Run benchmarks on real data:")
        console.print(f"  uv run python scripts/benchmark_embedding_quality.py --db {db_path}")
        console.print(f"  uv run python scripts/benchmark_embeddings.py --db {db_path}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Load interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Load failed: {e}[/red]")
        logger.exception("load_failed", error=str(e))
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
