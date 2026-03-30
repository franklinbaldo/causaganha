from collections import Counter


#!/usr/bin/env python3

GOOD_ACCURACY_THRESHOLD = 70

"""Testa com 4 frases-chave: WIN, LOSS, UNKNOWN, PARTIAL."""

import os

import duckdb
import numpy as np
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table


console = Console()


_genai_client = None


def get_embedding(text: str) -> list[float]:
    """Get embedding."""
    result = _genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=[text],
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return result.embeddings[0].values


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
    """Testar com 4 frases-chave (WIN, LOSS, UNKNOWN, PARTIAL)."""
    console.print("\n[bold cyan]🎯 Teste: 4 Frases-Chave (WIN/LOSS/UNKNOWN/PARTIAL)[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    global _genai_client  # noqa: PLW0603
    _genai_client = genai.Client(api_key=api_key)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    # Definir as 4 frases-chave
    frases = {
        "WIN": "O autor da ação judicial venceu a causa e o réu foi condenado a pagar.",
        "LOSS": "O réu venceu a ação judicial e o pedido do autor foi negado e julgado improcedente.",
        "UNKNOWN": "Este é apenas um despacho processual ou intimação, sem julgamento definitivo do mérito da ação.",
        "PARTIAL": "A decisão foi parcialmente favorável ao autor e parcialmente ao réu, com procedência parcial.",
    }

    console.print(
        Panel(
            f"[green]WIN:[/green] {frases['WIN']}\n\n"
            f"[red]LOSS:[/red] {frases['LOSS']}\n\n"
            f"[yellow]UNKNOWN:[/yellow] {frases['UNKNOWN']}\n\n"
            f"[cyan]PARTIAL:[/cyan] {frases['PARTIAL']}",
            title="4 Frases de Referência",
        ),
    )

    # Gerar embeddings das frases-chave
    console.print("\n[yellow]Gerando embeddings das 4 frases-chave...[/yellow]")

    embeddings_ref = {
        "WIN": get_embedding(frases["WIN"]),
        "LOSS": get_embedding(frases["LOSS"]),
        "UNKNOWN": get_embedding(frases["UNKNOWN"]),
        "PARTIAL": get_embedding(frases["PARTIAL"]),
    }

    console.print("[green]✓ 4 embeddings gerados[/green]\n")

    # Carregar TODAS as 30 decisões do ground truth
    decisoes = conn.execute("""
        SELECT intimation_id, outcome, texto
        FROM ground_truth
        ORDER BY outcome, intimation_id
    """).fetchall()

    console.print(f"[cyan]Testando com {len(decisoes)} decisões do ground truth[/cyan]\n")

    # Testar cada decisão
    results = []
    correct = 0
    total = 0

    for intimation_id, outcome_real, texto in track(decisoes, description="Testando"):
        # Chunking
        chunks = chunk_text(texto)
        chunk_embeddings = [get_embedding(chunk) for chunk in chunks]

        # Calcular similaridade máxima com CADA frase
        max_similarities = {}

        for outcome_type, ref_emb in embeddings_ref.items():
            max_sim = max([cosine_similarity(chunk_emb, ref_emb) for chunk_emb in chunk_embeddings])
            max_similarities[outcome_type] = max_sim

        # Classificar baseado na MAIOR similaridade entre as 4
        outcome_previsto = max(max_similarities, key=max_similarities.get)
        max_score = max_similarities[outcome_previsto]

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
                "scores": max_similarities,
                "max_score": max_score,
                "acertou": acertou,
            },
        )

    # Calcular acurácia
    acuracia = (correct / total) * 100

    console.print("\n[bold]📊 Resultado Geral:[/bold]")
    console.print(f"  Acertos: {correct}/{total}")
    console.print(
        f"  Acurácia: [{'green' if acuracia >= GOOD_ACCURACY_THRESHOLD else 'red'}]{acuracia:.1f}%[/]\n"
    )

    # Matriz de confusão

    conf_table = Table(title="Matriz de Confusão")
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

    # Mostrar exemplos
    console.print("\n[bold green]✓ Exemplos de ACERTOS:[/bold green]\n")
    acertos = [r for r in results if r["acertou"]][:3]
    for r in acertos:
        console.print(f"ID {r['id']}: {r['real']} (previsto: {r['previsto']})")
        console.print(f"  Scores: {', '.join([f'{k}: {v:.3f}' for k, v in r['scores'].items()])}\n")

    console.print("[bold red]✗ Exemplos de ERROS:[/bold red]\n")
    erros = [r for r in results if not r["acertou"]][:3]
    for r in erros:
        console.print(f"ID {r['id']}: {r['real']} (previsto ERRADO: {r['previsto']})")
        console.print(f"  Scores: {', '.join([f'{k}: {v:.3f}' for k, v in r['scores'].items()])}\n")

    # Comparação final
    console.print(
        Panel(
            "[bold]Comparação de Métodos:[/bold]\n\n"
            f"[cyan]4 Frases Simples:[/cyan] {acuracia:.1f}% (ESTE TESTE)\n"
            "[red]2 Frases Simples:[/red] 20.0% (só WIN/LOSS)\n"
            "[yellow]Frases Genéricas:[/yellow] 13.3%\n"
            "[green]RAG k-NN:[/green] 83.3%\n"
            "[magenta]LLM:[/magenta] ~85%\n\n"
            "[bold]Custo:[/bold]\n"
            "  4 Frases: $0.000004 (4 embeddings + comparação)\n"
            "  RAG k-NN: $0.000008\n"
            "  LLM: $0.000420\n\n"
            f"[bold]Veredicto:[/bold] "
            f"{'✅ Funciona muito bem!' if acuracia >= GOOD_ACCURACY_THRESHOLD else '⚠️ Melhor que 2 frases mas ainda abaixo do RAG'}",
            title="📊 Resultado Final",
        ),
    )

    conn.close()


if __name__ == "__main__":
    main()
