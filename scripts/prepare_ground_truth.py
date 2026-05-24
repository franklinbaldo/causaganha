
# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys
for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass

from collections import Counter


#!/usr/bin/env python3
"""Preparar ground truth de decisões validadas para RAG."""

import argparse
import sys

import duckdb
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table


console = Console()


# Stratified sampling targets each (tribunal x outcome x confidence-bucket) cell
# and tries to draw at least MIN_PER_CELL rows per cell, up to TARGET_TOTAL rows.
# The goal is a ground-truth set that reflects the full shape of the data, not
# just the cases that happen to have the highest confidence.
STRATIFIED_CONFIDENCE_BUCKETS: tuple[tuple[float, float, str], ...] = (
    (0.6, 0.7, "low"),
    (0.7, 0.8, "mid"),
    (0.8, 0.9, "high"),
    (0.9, 1.001, "top"),
)
STRATIFIED_OUTCOMES = ("procedente", "parcialmente procedente", "improcedente")
STRATIFIED_MIN_PER_CELL = 10
STRATIFIED_TARGET_TOTAL = 500


def _bucket_for(conf: float) -> str | None:
    """Return the name of the confidence bucket a score falls into."""
    for low, high, name in STRATIFIED_CONFIDENCE_BUCKETS:
        if low <= conf < high:
            return name
    return None


def run_stratified_sampling(
    conn: duckdb.DuckDBPyConnection,
    target: int = STRATIFIED_TARGET_TOTAL,
    min_per_cell: int = STRATIFIED_MIN_PER_CELL,
) -> list[tuple]:
    """Draw a stratified sample of classifications for ground-truth review.

    Samples by (sigla_tribunal x outcome x confidence_bucket). Each cell gets at
    least ``min_per_cell`` rows when available; remaining capacity up to
    ``target`` is distributed proportionally to cell sizes.
    """
    buckets_sql = ", ".join(
        f"({low}, {high}, '{name}')" for low, high, name in STRATIFIED_CONFIDENCE_BUCKETS
    )
    outcomes_sql = ", ".join(f"'{o}'" for o in STRATIFIED_OUTCOMES)

    conn.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _gt_candidates AS
        SELECT
            da.intimation_id,
            da.outcome,
            da.winner_party_name,
            da.loser_party_name,
            da.winner_lawyer_oab,
            da.loser_lawyer_oab,
            da.confidence_score,
            i.texto,
            i.sigla_tribunal,
            b.bucket
        FROM decision_analysis da
        JOIN intimations i ON da.intimation_id = i.id
        JOIN (
            SELECT * FROM (VALUES {buckets_sql}) AS t(lo, hi, bucket)
        ) b ON da.confidence_score >= b.lo AND da.confidence_score < b.hi
        WHERE da.outcome IN ({outcomes_sql})
          AND i.texto IS NOT NULL
          AND LENGTH(i.texto) BETWEEN 500 AND 8000
        """
    )

    # Show cell sizes up front so operators can spot holes.
    cells = conn.execute(
        """
        SELECT sigla_tribunal, outcome, bucket, COUNT(*) AS n
        FROM _gt_candidates
        GROUP BY 1, 2, 3
        ORDER BY n DESC
        """
    ).fetchall()
    console.print(f"[cyan]Células (tribunal x outcome x bucket): {len(cells)}[/cyan]")

    # Seed: take up to min_per_cell per cell, randomly ordered per cell.
    seeded = conn.execute(
        f"""
        WITH ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY sigla_tribunal, outcome, bucket
                       ORDER BY RANDOM()
                   ) AS rk
            FROM _gt_candidates
        )
        SELECT intimation_id, outcome, texto, winner_party_name, loser_party_name,
               winner_lawyer_oab, loser_lawyer_oab, confidence_score,
               LENGTH(texto) AS text_length
        FROM ranked
        WHERE rk <= {min_per_cell}
        """
    ).fetchall()

    remaining = max(0, target - len(seeded))
    if remaining > 0:
        seeded_ids = {row[0] for row in seeded}
        placeholders = ",".join(["?"] * len(seeded_ids)) if seeded_ids else "NULL"
        extra = conn.execute(
            f"""
            SELECT intimation_id, outcome, texto, winner_party_name, loser_party_name,
                   winner_lawyer_oab, loser_lawyer_oab, confidence_score,
                   LENGTH(texto) AS text_length
            FROM _gt_candidates
            WHERE intimation_id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT {remaining}
            """,
            list(seeded_ids),
        ).fetchall()
        seeded.extend(extra)

    return seeded[:target]


def main() -> None:
    """Preparar ground truth validado."""
    parser = argparse.ArgumentParser(
        description="Prepara ground truth para validação do classificador."
    )
    parser.add_argument(
        "--stratified",
        action="store_true",
        help="Amostragem estratificada por (tribunal x outcome x bucket de confidence).",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=STRATIFIED_TARGET_TOTAL,
        help="Tamanho-alvo do conjunto estratificado (padrão: 500).",
    )
    parser.add_argument(
        "--min-per-cell",
        type=int,
        default=STRATIFIED_MIN_PER_CELL,
        help="Mínimo de amostras por célula antes da amostragem proporcional.",
    )
    args = parser.parse_args()

    console.print("\n[bold cyan]📋 Preparação de Ground Truth[/bold cyan]\n")

    # Conectar ao banco
    conn = duckdb.connect("data/causaganha.duckdb")

    # Criar tabela de ground truth se não existir
    console.print("[yellow]Criando tabela de ground truth...[/yellow]")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ground_truth (
            intimation_id BIGINT PRIMARY KEY,
            outcome VARCHAR NOT NULL,
            texto VARCHAR NOT NULL,
            winner_party VARCHAR,
            loser_party VARCHAR,
            winner_lawyer_oab VARCHAR,
            loser_lawyer_oab VARCHAR,
            confidence_score DOUBLE,
            validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            validation_source VARCHAR DEFAULT 'llm_high_confidence'
        )
    """)

    if args.stratified:
        console.print(
            "\n[yellow]Amostragem estratificada por (tribunal x outcome x "
            "confidence bucket)...[/yellow]\n"
        )
        candidates = run_stratified_sampling(
            conn,
            target=args.target,
            min_per_cell=args.min_per_cell,
        )
        console.print(f"✓ {len(candidates)} candidatos estratificados\n")
    else:
        console.print("\n[yellow]Buscando decisões com alta confiança da LLM...[/yellow]\n")
        candidates = conn.execute("""
            SELECT
                ar.intimation_id,
                ar.outcome,
                i.texto,
                ar.winner_party_name,
                ar.loser_party_name,
                ar.winner_lawyer_oab,
                ar.loser_lawyer_oab,
                ar.confidence_score,
                LENGTH(i.texto) as text_length
            FROM analysis_results ar
            JOIN intimations i ON ar.intimation_id = i.id
            WHERE ar.confidence_score >= 0.90
              AND ar.outcome IN ('WIN', 'LOSS', 'PARTIAL', 'UNKNOWN')
              AND i.texto IS NOT NULL
              AND LENGTH(i.texto) BETWEEN 500 AND 8000
            ORDER BY ar.confidence_score DESC
            LIMIT 100
        """).fetchall()
        console.print(f"✓ Encontrados {len(candidates)} candidatos com confiança ≥ 90%\n")

    # Estatísticas por outcome
    table = Table(title="Distribuição de Candidatos")
    table.add_column("Outcome", style="cyan")
    table.add_column("Count", style="yellow")
    table.add_column("Avg Confidence", style="green")

    outcome_counts = Counter(c[1] for c in candidates)
    outcome_confidence = {}

    for outcome in outcome_counts:
        confs = [c[7] for c in candidates if c[1] == outcome]
        outcome_confidence[outcome] = sum(confs) / len(confs)

    for outcome, count in outcome_counts.most_common():
        table.add_row(outcome, str(count), f"{outcome_confidence[outcome]:.2f}")

    console.print(table)

    if args.stratified:
        # Stratified sampling already balanced the candidates; use them all.
        ground_truth_items = list(candidates)
        by_outcome = Counter(item[1] for item in ground_truth_items)
        console.print("\n[bold]Distribuição estratificada final:[/bold]")
        for outcome, count in by_outcome.most_common():
            console.print(f"  {outcome}: {count}")
    else:
        # Selecionar subset balanceado (modo clássico)
        console.print("\n[bold]Selecionando subset balanceado para ground truth:[/bold]\n")
        target_per_outcome = 25
        ground_truth_items = []
        for outcome in ["WIN", "LOSS", "PARTIAL", "UNKNOWN"]:
            items = [c for c in candidates if c[1] == outcome][:target_per_outcome]
            ground_truth_items.extend(items)
            console.print(f"  {outcome:8s}: {len(items)} decisões")

    console.print(f"\n[green]Total selecionado: {len(ground_truth_items)} decisões[/green]\n")

    # Mostrar algumas amostras
    console.print("[bold]Amostras do Ground Truth:[/bold]\n")

    for i, item in enumerate(ground_truth_items[:3], 1):
        intimation_id, outcome, texto, winner, loser, w_oab, l_oab, conf, length = item
        console.print(f"[cyan]{i}. ID {intimation_id}[/cyan]")
        console.print(f"   Outcome: {outcome} (confiança: {conf:.2f})")
        console.print(f"   Winner: {winner} ({w_oab})")
        console.print(f"   Loser: {loser} ({l_oab})")
        console.print(f"   Texto: {length} chars")
        console.print(f"   Preview: {texto[:150]}...\n")

    # Confirmar (auto-confirm em modo não-interativo)

    if sys.stdin.isatty():
        if not Confirm.ask("\n[yellow]Inserir estes dados na tabela ground_truth?[/yellow]"):
            console.print("[red]Operação cancelada[/red]")
            return
    else:
        console.print("\n[green]✓ Modo não-interativo: prosseguindo automaticamente[/green]")

    # Inserir
    console.print("\n[yellow]Inserindo no banco de dados...[/yellow]")

    for item in ground_truth_items:
        intimation_id, outcome, texto, winner, loser, w_oab, l_oab, conf, _ = item
        conn.execute(
            """
            INSERT OR REPLACE INTO ground_truth
            (intimation_id, outcome, texto, winner_party, loser_party,
             winner_lawyer_oab, loser_lawyer_oab, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (intimation_id, outcome, texto, winner, loser, w_oab, l_oab, conf),
        )

    conn.commit()

    # Estatísticas finais
    stats = conn.execute("""
        SELECT
            outcome,
            COUNT(*) as count,
            AVG(confidence_score) as avg_conf,
            AVG(LENGTH(texto)) as avg_length
        FROM ground_truth
        GROUP BY outcome
        ORDER BY outcome
    """).fetchall()

    console.print("\n[bold green]✓ Ground Truth Criado com Sucesso![/bold green]\n")

    final_table = Table(title="Ground Truth - Estatísticas Finais")
    final_table.add_column("Outcome", style="cyan")
    final_table.add_column("Count", style="yellow")
    final_table.add_column("Avg Confidence", style="green")
    final_table.add_column("Avg Length", style="magenta")

    for outcome, count, avg_conf, avg_len in stats:
        final_table.add_row(outcome, str(count), f"{avg_conf:.2f}", f"{int(avg_len)} chars")

    console.print(final_table)

    console.print("\n[bold]Próximos passos:[/bold]")
    console.print("  1. python scripts/index_ground_truth.py  # Indexar no LanceDB")
    console.print("  2. python scripts/test_rag_accuracy.py   # Testar RAG com k-NN\n")

    conn.close()


if __name__ == "__main__":
    main()
