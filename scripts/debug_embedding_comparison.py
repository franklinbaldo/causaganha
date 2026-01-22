#!/usr/bin/env python3
"""Debug detalhado do processo de comparação de embeddings."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import duckdb
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from causaganha.infrastructure.ai.embeddings import EmbeddingAnalyzer


console = Console()


def main():
    """Analisar em detalhes como funciona a comparação."""
    console.print("\n[bold cyan]🔬 DEBUG: Como funciona a comparação de embeddings[/bold cyan]\n")

    # Buscar UMA decisão para análise detalhada
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    decision = conn.execute(
        """
        SELECT
            ar.intimation_id,
            ar.outcome as llm_outcome,
            i.texto
        FROM analysis_results ar
        JOIN intimations i ON ar.intimation_id = i.id
        WHERE ar.outcome = 'WIN'
          AND LENGTH(i.texto) BETWEEN 1000 AND 2000
        LIMIT 1
    """,
    ).fetchone()

    if not decision:
        console.print("[red]Nenhuma decisão encontrada[/red]")
        return

    intimation_id, llm_outcome, texto = decision

    console.print(f"[cyan]Processo ID:[/cyan] {intimation_id}")
    console.print(f"[cyan]Outcome LLM:[/cyan] {llm_outcome}")
    console.print(f"[cyan]Tamanho do texto:[/cyan] {len(texto)} chars\n")

    # Inicializar analyzer
    analyzer = EmbeddingAnalyzer()

    # PASSO 1: Mostrar chunking
    console.print(Panel("[bold]PASSO 1: CHUNKING DO TEXTO[/bold]", expand=False))
    chunks = analyzer.chunk_text(texto, chunk_size=400, overlap=100)

    console.print(f"\n[yellow]Total de chunks:[/yellow] {len(chunks)}\n")

    for i, chunk in enumerate(chunks[:3], 1):  # Mostrar só os 3 primeiros
        console.print(f"[cyan]Chunk {i}:[/cyan] ({len(chunk)} chars)")
        console.print(f"[dim]{chunk[:150]}...[/dim]\n")

    # PASSO 2: Mostrar frases de referência
    console.print(Panel("[bold]PASSO 2: FRASES DE REFERÊNCIA[/bold]", expand=False))

    for outcome, phrases in list(analyzer.reference_phrases.items())[:2]:
        console.print(f"\n[yellow]{outcome}:[/yellow]")
        for phrase in phrases[:3]:
            console.print(f"  • {phrase}")

    # PASSO 3: Calcular embeddings e similaridades
    console.print("\n")
    console.print(Panel("[bold]PASSO 3: CÁLCULO DE SIMILARIDADES[/bold]", expand=False))

    chunk_embeddings = [analyzer._get_embedding(chunk) for chunk in chunks]
    console.print(f"\n[green]✓[/green] Embeddings calculados: {len(chunk_embeddings)} chunks")

    # Calcular similaridades detalhadas
    console.print("\n[bold]Similaridades por chunk:[/bold]\n")

    detailed_scores = {}

    for chunk_idx, chunk_emb in enumerate(chunk_embeddings):
        console.print(f"[cyan]Chunk {chunk_idx + 1}:[/cyan]")

        chunk_scores = {}
        for outcome, ref_embeddings in analyzer.reference_embeddings.items():
            similarities = [
                analyzer._cosine_similarity(chunk_emb, ref_emb) for ref_emb in ref_embeddings
            ]
            max_sim = max(similarities)
            avg_sim = np.mean(similarities)
            chunk_scores[outcome] = {"max": max_sim, "avg": avg_sim, "all": similarities}

            console.print(f"  {outcome:12s}: max={max_sim:.4f}, avg={avg_sim:.4f}")

        detailed_scores[chunk_idx] = chunk_scores
        console.print()

    # PASSO 4: Agregação
    console.print("\n")
    console.print(Panel("[bold]PASSO 4: AGREGAÇÃO (COMO ESTÁ AGORA)[/bold]", expand=False))

    console.print("\n[yellow]Método atual: MAX entre todos os chunks[/yellow]\n")

    final_scores_max = {}
    for outcome in analyzer.reference_phrases.keys():
        all_chunk_maxes = [
            detailed_scores[chunk_idx][outcome]["max"] for chunk_idx in range(len(chunks))
        ]
        final_scores_max[outcome] = max(all_chunk_maxes)

    table = Table(title="Scores Finais (MAX)")
    table.add_column("Outcome", style="cyan")
    table.add_column("Score", style="yellow")
    table.add_column("Diferença do 2º", style="green")

    sorted_scores = sorted(final_scores_max.items(), key=lambda x: -x[1])
    best_score = sorted_scores[0][1]

    for outcome, score in sorted_scores:
        diff = score - sorted_scores[1][1] if outcome == sorted_scores[0][0] else score - best_score
        table.add_row(outcome, f"{score:.6f}", f"{diff:+.6f}")

    console.print(table)

    # PROBLEMA: Scores muito próximos!
    console.print(
        f"\n[red]⚠️  PROBLEMA: Diferença de apenas {sorted_scores[0][1] - sorted_scores[1][1]:.6f} "
        f"entre 1º e 2º lugar![/red]",
    )

    # PASSO 5: Testar outras agregações
    console.print("\n")
    console.print(Panel("[bold]PASSO 5: OUTRAS ESTRATÉGIAS DE AGREGAÇÃO[/bold]", expand=False))

    # Estratégia 1: Média dos top-3 chunks
    console.print("\n[yellow]Estratégia 1: MÉDIA dos top-3 chunks por outcome[/yellow]\n")

    final_scores_top3 = {}
    for outcome in analyzer.reference_phrases.keys():
        all_chunk_maxes = [
            detailed_scores[chunk_idx][outcome]["max"] for chunk_idx in range(len(chunks))
        ]
        top3 = sorted(all_chunk_maxes, reverse=True)[:3]
        final_scores_top3[outcome] = np.mean(top3)

    table2 = Table(title="Scores Finais (Média Top-3)")
    table2.add_column("Outcome", style="cyan")
    table2.add_column("Score", style="yellow")
    table2.add_column("Diferença", style="green")

    sorted_scores2 = sorted(final_scores_top3.items(), key=lambda x: -x[1])
    best_score2 = sorted_scores2[0][1]

    for outcome, score in sorted_scores2:
        diff = (
            score - sorted_scores2[1][1] if outcome == sorted_scores2[0][0] else score - best_score2
        )
        table2.add_row(outcome, f"{score:.6f}", f"{diff:+.6f}")

    console.print(table2)

    # Estratégia 2: Normalização via Softmax
    console.print("\n[yellow]Estratégia 2: Normalização SOFTMAX[/yellow]\n")

    def softmax(scores_dict):
        values = np.array(list(scores_dict.values()))
        exp_values = np.exp(values - np.max(values))  # Subtract max for numerical stability
        return dict(zip(scores_dict.keys(), exp_values / exp_values.sum(), strict=False))

    normalized_scores = softmax(final_scores_max)

    table3 = Table(title="Scores Normalizados (Softmax)")
    table3.add_column("Outcome", style="cyan")
    table3.add_column("Score Original", style="yellow")
    table3.add_column("Score Normalizado", style="green")

    for outcome in sorted(normalized_scores.keys(), key=lambda x: -normalized_scores[x]):
        table3.add_row(
            outcome,
            f"{final_scores_max[outcome]:.6f}",
            f"{normalized_scores[outcome]:.4f}",
        )

    console.print(table3)

    # Estratégia 3: Média ponderada por posição do chunk
    console.print(
        "\n[yellow]Estratégia 3: Ponderação por POSIÇÃO (chunks iniciais = mais peso)[/yellow]\n",
    )

    final_scores_weighted = {}
    for outcome in analyzer.reference_phrases.keys():
        weighted_sum = 0
        total_weight = 0
        for chunk_idx in range(len(chunks)):
            # Peso decrescente: primeiro chunk = 1.0, último = 0.3
            weight = 1.0 - (chunk_idx / len(chunks)) * 0.7
            weighted_sum += detailed_scores[chunk_idx][outcome]["max"] * weight
            total_weight += weight
        final_scores_weighted[outcome] = weighted_sum / total_weight

    table4 = Table(title="Scores Ponderados")
    table4.add_column("Outcome", style="cyan")
    table4.add_column("Score", style="yellow")
    table4.add_column("Diferença", style="green")

    sorted_scores4 = sorted(final_scores_weighted.items(), key=lambda x: -x[1])
    best_score4 = sorted_scores4[0][1]

    for outcome, score in sorted_scores4:
        diff = (
            score - sorted_scores4[1][1] if outcome == sorted_scores4[0][0] else score - best_score4
        )
        table4.add_row(outcome, f"{score:.6f}", f"{diff:+.6f}")

    console.print(table4)

    # Comparação final
    console.print("\n")
    console.print(Panel("[bold]COMPARAÇÃO DE ESTRATÉGIAS[/bold]", expand=False))

    comparison = Table()
    comparison.add_column("Estratégia", style="cyan")
    comparison.add_column("Vencedor", style="yellow")
    comparison.add_column("Score", style="green")
    comparison.add_column("Diferença 1º-2º", style="magenta")

    strategies = [
        ("MAX global", sorted_scores, "atual"),
        ("Média Top-3", sorted_scores2, ""),
        ("Softmax", sorted(normalized_scores.items(), key=lambda x: -x[1]), ""),
        ("Ponderado por posição", sorted_scores4, ""),
    ]

    for name, scores, note in strategies:
        winner = scores[0][0]
        score = scores[0][1]
        diff = scores[0][1] - scores[1][1]
        style = "bold green" if diff > 0.01 else "red"
        comparison.add_row(
            f"{name} {note}",
            winner,
            f"{score:.6f}",
            f"[{style}]{diff:.6f}[/{style}]",
        )

    console.print(comparison)

    console.print(
        f"\n[bold cyan]LLM classificou como:[/bold cyan] [green]{llm_outcome}[/green]",
    )

    conn.close()


if __name__ == "__main__":
    main()
