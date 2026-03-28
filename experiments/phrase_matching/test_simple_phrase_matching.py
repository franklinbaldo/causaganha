from collections import Counter


#!/usr/bin/env python3
"""Testa a ideia original: comparação direta com 2 frases-chave."""

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


def main() -> None:
    """Testar com 2 frases-chave simples."""
    console.print("\n[bold cyan]🎯 Teste: Comparação com 2 Frases-Chave[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    genai.configure(api_key=api_key)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    # Definir as 2 frases-chave
    console.print("[bold]📝 Frases-Chave:[/bold]\n")

    frases = {
        "AUTOR_VENCEU": "O autor da ação judicial venceu a causa e o réu foi condenado a pagar.",
        "REU_VENCEU": "O réu venceu a ação judicial e o pedido do autor foi negado.",
    }

    console.print(
        Panel(
            f"[cyan]Frase 1 (AUTOR VENCEU):[/cyan]\n{frases['AUTOR_VENCEU']}\n\n"
            f"[yellow]Frase 2 (RÉU VENCEU):[/yellow]\n{frases['REU_VENCEU']}",
            title="Frases de Referência",
        ),
    )

    # Gerar embeddings das frases-chave
    console.print("\n[yellow]Gerando embeddings das frases-chave...[/yellow]")

    emb_autor_venceu = get_embedding(frases["AUTOR_VENCEU"])
    emb_reu_venceu = get_embedding(frases["REU_VENCEU"])

    console.print("[green]✓ Embeddings gerados[/green]\n")

    # Carregar ground truth para testar
    decisoes = conn.execute("""
        SELECT intimation_id, outcome, texto
        FROM ground_truth
        WHERE outcome IN ('WIN', 'LOSS')
        ORDER BY outcome, intimation_id
    """).fetchall()

    console.print(
        f"[cyan]Testando com {len(decisoes)} decisões do ground truth (WIN e LOSS)[/cyan]\n",
    )

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
            [cosine_similarity(chunk_emb, emb_autor_venceu) for chunk_emb in chunk_embeddings],
        )

        max_sim_reu = max(
            [cosine_similarity(chunk_emb, emb_reu_venceu) for chunk_emb in chunk_embeddings],
        )

        # Classificar baseado na maior similaridade
        outcome_previsto = "WIN" if max_sim_autor > max_sim_reu else "LOSS"

        # Verificar acerto
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
                "diff": abs(max_sim_autor - max_sim_reu),
                "acertou": acertou,
            },
        )

    # Calcular acurácia
    acuracia = (correct / total) * 100

    console.print("\n[bold]📊 Resultado:[/bold]")
    console.print(f"  Acertos: {correct}/{total}")
    console.print(f"  Acurácia: [{'green' if acuracia >= 70 else 'red'}]{acuracia:.1f}%[/]\n")

    # Mostrar matriz de confusão
    conf_table = Table(title="Matriz de Confusão")
    conf_table.add_column("Real", style="cyan")
    conf_table.add_column("Previsto", style="yellow")
    conf_table.add_column("Count", style="green")

    confusion = Counter([(r["real"], r["previsto"]) for r in results])

    for (real, previsto), count in confusion.most_common():
        match = "✓" if real == previsto else "✗"
        conf_table.add_row(real, f"{match} {previsto}", str(count))

    console.print(conf_table)

    # Analisar diferença de scores
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

    # Mostrar exemplos de acertos e erros
    console.print("\n[bold green]✓ Exemplos de ACERTOS:[/bold green]\n")

    acertos = [r for r in results if r["acertou"]][:3]
    for r in acertos:
        console.print(f"ID {r['id']}: {r['real']} (previsto: {r['previsto']})")
        console.print(
            f"  Sim AUTOR: {r['sim_autor']:.4f} | Sim RÉU: {r['sim_reu']:.4f} | Diff: {r['diff']:.4f}\n",
        )

    console.print("[bold red]✗ Exemplos de ERROS:[/bold red]\n")

    erros = [r for r in results if not r["acertou"]][:3]
    for r in erros:
        console.print(f"ID {r['id']}: {r['real']} (previsto ERRADO: {r['previsto']})")
        console.print(
            f"  Sim AUTOR: {r['sim_autor']:.4f} | Sim RÉU: {r['sim_reu']:.4f} | Diff: {r['diff']:.4f}",
        )
        console.print("  [yellow]Problema: Scores muito próximos![/yellow]\n")

    # Comparação com outros métodos
    console.print(
        Panel(
            "[bold]Comparação de Métodos:[/bold]\n\n"
            f"[red]2 Frases Simples:[/red] {acuracia:.1f}% (este teste)\n"
            "[yellow]Frases Genéricas (múltiplas):[/yellow] 13.3% (teste anterior)\n"
            "[green]RAG k-NN (ground truth):[/green] 83.3% (validado)\n"
            "[cyan]LLM (Gemini Flash):[/cyan] ~85% (baseline)\n\n"
            f"[bold]Veredicto:[/bold] {'✅ Melhor que frases múltiplas!' if acuracia > 13.3 else '❌ Não funcionou bem'}",
            title="📊 Comparação",
        ),
    )

    conn.close()


if __name__ == "__main__":
    main()
