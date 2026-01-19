#!/usr/bin/env python3
"""Preparar ground truth de decisões validadas para RAG."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import duckdb
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

console = Console()


def main():
    """Preparar ground truth validado."""
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

    # Buscar decisões da LLM com alta confiança para usar como ground truth
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

    from collections import Counter
    outcome_counts = Counter(c[1] for c in candidates)
    outcome_confidence = {}

    for outcome in outcome_counts:
        confs = [c[7] for c in candidates if c[1] == outcome]
        outcome_confidence[outcome] = sum(confs) / len(confs)

    for outcome, count in outcome_counts.most_common():
        table.add_row(outcome, str(count), f"{outcome_confidence[outcome]:.2f}")

    console.print(table)

    # Selecionar subset balanceado
    console.print("\n[bold]Selecionando subset balanceado para ground truth:[/bold]\n")

    # Queremos ~25 de cada tipo para começar
    target_per_outcome = 25
    ground_truth_items = []

    for outcome in ['WIN', 'LOSS', 'PARTIAL', 'UNKNOWN']:
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
    import sys
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
        conn.execute("""
            INSERT OR REPLACE INTO ground_truth
            (intimation_id, outcome, texto, winner_party, loser_party,
             winner_lawyer_oab, loser_lawyer_oab, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (intimation_id, outcome, texto, winner, loser, w_oab, l_oab, conf))

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
