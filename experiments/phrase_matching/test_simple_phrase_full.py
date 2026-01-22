#!/usr/bin/env python3
"""Testa 2 frases-chave com TODAS as 30 decisões do ground truth."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

import duckdb
import google.generativeai as genai
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table


console = Console()


def get_embedding(text: str) -> list[float]:
    """Get embedding."""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chunk text."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    return chunks


def main():
    """Testar com TODAS as 30 decisões do ground truth."""
    console.print("\n[bold cyan]🎯 Teste Completo: 2 Frases-Chave vs 30 Decisões[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    genai.configure(api_key=api_key)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    # Definir as 2 frases-chave
    frases = {
        "AUTOR_VENCEU": "O autor da ação judicial venceu a causa e o réu foi condenado a pagar.",
        "REU_VENCEU": "O réu venceu a ação judicial e o pedido do autor foi negado.",
    }

    console.print(
        Panel(
            f"[cyan]Frase AUTOR VENCEU:[/cyan]\n{frases['AUTOR_VENCEU']}\n\n"
            f"[yellow]Frase RÉU VENCEU:[/yellow]\n{frases['REU_VENCEU']}",
            title="Frases de Referência",
        )
    )

    # Gerar embeddings das frases-chave
    console.print("\n[yellow]Gerando embeddings das frases-chave...[/yellow]")

    emb_autor_venceu = get_embedding(frases["AUTOR_VENCEU"])
    emb_reu_venceu = get_embedding(frases["REU_VENCEU"])

    console.print("[green]✓ Embeddings gerados[/green]\n")

    # Carregar TODAS as 30 decisões do ground truth
    decisoes = conn.execute("""
        SELECT intimation_id, outcome, texto
        FROM ground_truth
        ORDER BY outcome, intimation_id
    """).fetchall()

    console.print(f"[cyan]Testando com {len(decisoes)} decisões do ground truth[/cyan]\n")

    # Contar distribuição
    from collections import Counter

    distribuicao = Counter([d[1] for d in decisoes])

    dist_table = Table(title="Distribuição do Ground Truth")
    dist_table.add_column("Outcome", style="cyan")
    dist_table.add_column("Count", style="yellow")

    for outcome, count in distribuicao.most_common():
        dist_table.add_row(outcome, str(count))

    console.print(dist_table)
    console.print()

    # Testar cada decisão
    results = []
    correct = 0
    total = 0

    for intimation_id, outcome_real, texto in track(decisoes, description="Testando"):
        # Chunking
        chunks = chunk_text(texto)
        chunk_embeddings = [get_embedding(chunk) for chunk in chunks]

        # Calcular similaridade máxima com cada frase
        max_sim_autor = max(
            [cosine_similarity(chunk_emb, emb_autor_venceu) for chunk_emb in chunk_embeddings]
        )

        max_sim_reu = max(
            [cosine_similarity(chunk_emb, emb_reu_venceu) for chunk_emb in chunk_embeddings]
        )

        # Classificar baseado na maior similaridade
        if max_sim_autor > max_sim_reu:
            outcome_previsto = "WIN"
        else:
            outcome_previsto = "LOSS"

        # Mapear UNKNOWN e PARTIAL
        # Se a diferença for muito pequena, talvez seja UNKNOWN
        diff = abs(max_sim_autor - max_sim_reu)

        # Verificar acerto
        # WIN deve prever WIN, LOSS deve prever LOSS
        # UNKNOWN e PARTIAL são ambíguos - vamos ver o que acontece
        acertou = outcome_previsto == outcome_real
        if acertou:
            correct += 1
        total += 1

        results.append(
            {
                "id": intimation_id,
                "real": outcome_real,
                "previsto": outcome_previsto,
                "sim_autor": max_sim_autor,
                "sim_reu": max_sim_reu,
                "diff": diff,
                "acertou": acertou,
            }
        )

    # Calcular acurácia
    acuracia = (correct / total) * 100

    console.print("\n[bold]📊 Resultado Geral:[/bold]")
    console.print(f"  Acertos: {correct}/{total}")
    console.print(f"  Acurácia: [{'green' if acuracia >= 70 else 'red'}]{acuracia:.1f}%[/]\n")

    # Matriz de confusão
    conf_table = Table(title="Matriz de Confusão Completa")
    conf_table.add_column("Real", style="cyan")
    conf_table.add_column("Previsto", style="yellow")
    conf_table.add_column("Count", style="green")

    confusion = Counter([(r["real"], r["previsto"]) for r in results])

    for (real, previsto), count in confusion.most_common():
        match = "✓" if real == previsto else "✗"
        conf_table.add_row(real, f"{match} {previsto}", str(count))

    console.print(conf_table)

    # Acurácia por tipo
    console.print("\n[bold]📊 Acurácia por Tipo:[/bold]\n")

    acc_table = Table()
    acc_table.add_column("Outcome Real", style="cyan")
    acc_table.add_column("Total", style="yellow")
    acc_table.add_column("Acertos", style="green")
    acc_table.add_column("Acurácia", style="magenta")

    for outcome in ["WIN", "LOSS", "PARTIAL", "UNKNOWN"]:
        outcome_results = [r for r in results if r["real"] == outcome]
        if outcome_results:
            outcome_total = len(outcome_results)
            outcome_correct = sum(1 for r in outcome_results if r["acertou"])
            outcome_acc = (outcome_correct / outcome_total) * 100
            acc_table.add_row(
                outcome,
                str(outcome_total),
                str(outcome_correct),
                f"{outcome_acc:.1f}%",
            )

    console.print(acc_table)

    # Análise de scores
    console.print("\n[bold]🔍 Análise de Scores:[/bold]\n")

    diffs = [r["diff"] for r in results]
    avg_diff = np.mean(diffs)
    min_diff = np.min(diffs)
    max_diff = np.max(diffs)

    stats_table = Table()
    stats_table.add_column("Métrica", style="cyan")
    stats_table.add_column("Valor", style="yellow")

    stats_table.add_row("Diferença Média", f"{avg_diff:.4f}")
    stats_table.add_row("Diferença Mínima", f"{min_diff:.4f}")
    stats_table.add_row("Diferença Máxima", f"{max_diff:.4f}")

    console.print(stats_table)

    # Comparação final
    console.print()
    console.print(
        Panel(
            "[bold]Comparação de Métodos (Teste Completo):[/bold]\n\n"
            f"[red]2 Frases Simples:[/red] {acuracia:.1f}% (ESTE TESTE)\n"
            "[yellow]Frases Genéricas:[/yellow] 13.3% (teste anterior)\n"
            "[green]RAG k-NN:[/green] 83.3% (validado)\n"
            "[cyan]LLM:[/cyan] ~85%\n\n"
            f"[bold]Custo:[/bold]\n"
            f"  2 Frases: $0.000003 (2 embeddings + comparação)\n"
            f"  RAG k-NN: $0.000008 (embeddings + busca)\n"
            f"  LLM: $0.000420\n\n"
            f"[bold]Veredicto:[/bold] "
            f"{'✅ Simples e eficaz!' if acuracia >= 70 else '⚠️ Precisa melhorar para UNKNOWN/PARTIAL'}",
            title="📊 Resultado Final",
        )
    )

    conn.close()


if __name__ == "__main__":
    main()
