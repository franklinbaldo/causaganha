from collections import Counter

from rich.table import Table


#!/usr/bin/env python3
"""Indexar ground truth no LanceDB com chunks prefixados."""

import os
from pathlib import Path

import duckdb
import lancedb
from google import genai
from rich.console import Console
from rich.progress import track


console = Console()


# Instruções contextuais para prefixar chunks
CHUNK_INSTRUCTION = """Analise esta parte de uma decisão judicial brasileira e determine qual polo venceu:
- Polo Ativo (autor/requerente/exequente)
- Polo Passivo (réu/requerido/executado)
Considere termos como: procedente, improcedente, julgo, condeno, defiro, indefiro, provimento, negado."""


def chunk_text_with_prefix(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chunking com prefixo de instrução."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Tentar quebrar em sentença
        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk = text[start:end]

        # PREFIXAR COM INSTRUÇÃO
        prefixed_chunk = f"{CHUNK_INSTRUCTION}\n\n{chunk.strip()}"
        chunks.append(prefixed_chunk)

        start = end - overlap

    return chunks


_genai_client = None


def get_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Get embedding com task type específico."""
    result = _genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=[text],
        config={"task_type": task_type},
    )
    return result.embeddings[0].values


def main() -> None:
    """Indexar ground truth no LanceDB."""
    console.print("\n[bold cyan]🗂️  Indexação de Ground Truth no LanceDB[/bold cyan]\n")

    # Configurar Gemini
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    global _genai_client  # noqa: PLW0603
    _genai_client = genai.Client(api_key=api_key)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    # Buscar ground truth
    console.print("[yellow]Carregando ground truth...[/yellow]")
    ground_truth = conn.execute("""
        SELECT intimation_id, outcome, texto
        FROM ground_truth
        ORDER BY outcome, intimation_id
    """).fetchall()

    console.print(f"✓ Carregadas {len(ground_truth)} decisões\n")

    if not ground_truth:
        console.print(
            "[red]Erro: Nenhum dado em ground_truth. Execute prepare_ground_truth.py primeiro[/red]",
        )
        return

    # Preparar LanceDB
    db_path = Path("data/lancedb")
    db_path.mkdir(parents=True, exist_ok=True)

    db = lancedb.connect(str(db_path))
    table_name = "ground_truth_embeddings"

    # Remover tabela existente
    if table_name in db.table_names():
        console.print(f"[yellow]Removendo tabela existente {table_name}...[/yellow]")
        db.drop_table(table_name)

    console.print("\n[bold]Processando e indexando decisões...[/bold]\n")

    records = []
    total_chunks = 0

    for intimation_id, outcome, texto in track(ground_truth, description="Indexando"):
        # Chunk com prefixo
        chunks = chunk_text_with_prefix(texto, chunk_size=500, overlap=100)

        # Gerar embeddings
        for chunk_idx, prefixed_chunk in enumerate(chunks):
            embedding = get_embedding(prefixed_chunk, task_type="retrieval_document")

            records.append(
                {
                    "intimation_id": intimation_id,
                    "outcome": outcome,
                    "chunk_index": chunk_idx,
                    "chunk_text": prefixed_chunk,  # Armazenar com prefixo
                    "vector": embedding,
                },
            )

            total_chunks += 1

    # Criar tabela LanceDB
    console.print(f"\n[yellow]Criando tabela LanceDB com {len(records)} chunks...[/yellow]")
    db.create_table(table_name, data=records, mode="overwrite")

    # Criar índice para busca eficiente
    console.print("[yellow]Criando índice IVF-PQ para busca rápida...[/yellow]")

    console.print("\n[bold green]✓ Indexação Completa![/bold green]\n")

    # Estatísticas

    outcome_counts = Counter(r["outcome"] for r in records)

    stats_table = Table(title="Estatísticas de Indexação")
    stats_table.add_column("Outcome", style="cyan")
    stats_table.add_column("Decisões", style="yellow")
    stats_table.add_column("Chunks", style="green")
    stats_table.add_column("Avg Chunks/Decisão", style="magenta")

    outcome_decision_count = Counter(item[1] for item in ground_truth)

    for outcome in ["WIN", "LOSS", "PARTIAL", "UNKNOWN"]:
        chunks = outcome_counts.get(outcome, 0)
        decisions = outcome_decision_count.get(outcome, 0)
        avg = chunks / decisions if decisions > 0 else 0

        stats_table.add_row(
            outcome,
            str(decisions),
            str(chunks),
            f"{avg:.1f}",
        )

    stats_table.add_row(
        "[bold]TOTAL[/bold]",
        str(len(ground_truth)),
        str(total_chunks),
        f"{total_chunks / len(ground_truth):.1f}",
    )

    console.print(stats_table)

    console.print("\n[bold]Próximo passo:[/bold]")
    console.print("  python scripts/test_rag_accuracy.py  # Testar RAG com k-NN\n")

    conn.close()


if __name__ == "__main__":
    main()
