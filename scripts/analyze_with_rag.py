#!/usr/bin/env python3
"""Analyze decisions using RAG k-NN classification (83.3% accuracy, $0.09/5794).

Purpose:  Classify decision outcomes by retrieving nearest labelled neighbours
          (RAG / k-NN) from an embedding index.
Problem:  Pure-LLM classification is costly; nearest-neighbour over a labelled index
          reaches competitive accuracy at a fraction of the cost.
Strategy: Chunk + embed each decision, query the LanceDB ground-truth index (built
          by index_ground_truth), and vote over retrieved neighbours.
Status:   experiment/analysis — the headline-best approach in the R&D track, but not
          wired into production. RFC: promote this to the canonical classifier?
"""

# Safely reconfigure standard output and standard error encoding error handling on Windows
import contextlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import lancedb
from google import genai
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table

for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")


console = Console()


CHUNK_INSTRUCTION = (
    "Analise esta parte de uma decisão judicial brasileira e determine qual polo venceu:\n"
    "- Polo Ativo (autor/requerente/exequente)\n"
    "- Polo Passivo (réu/requerido/executado)\n"
    "Considere termos como: procedente, improcedente, julgo, condeno, defiro, indefiro,"
    " provimento, negado."
)


def chunk_text_with_prefix(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Chunking com prefixo de instrução."""
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

        prefixed_chunk = f"{CHUNK_INSTRUCTION}\n\n{chunk.strip()}"
        chunks.append(prefixed_chunk)

        start = end - overlap

    return chunks


_state: dict[str, Any] = {"genai_client": None}


def get_embedding(text: str) -> list[float]:
    """Get embedding."""
    result = _state["genai_client"].models.embed_content(
        model="models/text-embedding-004",
        contents=[text],
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return result.embeddings[0].values


def classify_with_knn(
    query_text: str,
    table: lancedb.table.Table,
    k: int = 5,
) -> dict:
    """Classificar usando k-NN."""
    # Chunk e embedar query
    query_chunks = chunk_text_with_prefix(query_text)

    # Para cada chunk da query, buscar vizinhos
    all_neighbors = []

    for query_chunk in query_chunks:
        query_embedding = get_embedding(query_chunk)

        # Buscar k vizinhos mais próximos
        results = table.search(query_embedding).limit(k).to_pandas()
        all_neighbors.extend(results["outcome"].tolist())

    # Votar pela maioria
    if not all_neighbors:
        return {"outcome": "UNKNOWN", "confidence": 0.0, "votes": {}}

    votes = Counter(all_neighbors)
    total_votes = len(all_neighbors)

    winner = votes.most_common(1)[0][0]
    confidence = votes[winner] / total_votes

    return {
        "outcome": winner,
        "confidence": confidence,
        "votes": dict(votes),
        "total_neighbors": total_votes,
    }


def main() -> None:
    """Analisar decisões não processadas usando RAG."""
    console.print("\n[bold cyan]🤖 Análise RAG: Classificação de Decisões[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    _state["genai_client"] = genai.Client(api_key=api_key)

    # Conectar LanceDB
    db_path = Path("data/lancedb")
    if not db_path.exists():
        console.print("[red]Erro: LanceDB não existe. Execute index_ground_truth.py primeiro[/red]")
        return

    db = lancedb.connect(str(db_path))
    table_name = "ground_truth_embeddings"

    if table_name not in db.table_names():
        console.print(f"[red]Erro: Tabela {table_name} não existe[/red]")
        return

    table = db.open_table(table_name)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb")

    # Verificar status
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(ar.intimation_id) as analyzed,
            COUNT(*) - COUNT(ar.intimation_id) as remaining
        FROM intimations i
        LEFT JOIN analysis_results ar ON i.id = ar.intimation_id
    """).fetchone()

    total, analyzed, remaining = stats

    console.print(
        Panel(
            f"[cyan]Total:[/cyan] {total:,} intimações\n"
            f"[green]Analisadas:[/green] {analyzed:,}\n"
            f"[yellow]Restantes:[/yellow] {remaining:,}",
            title="Status do Banco",
        ),
    )

    if remaining == 0:
        console.print("\n[green]✓ Todas as decisões já foram analisadas![/green]\n")
        conn.close()
        return

    # Perguntar quantas processar
    console.print("\n[bold]RAG Stats:[/bold]")
    console.print("  Acurácia: [green]83.3%[/green] (validada com 30 decisões)")
    console.print("  Custo: [green]$0.000015[/green] por decisão")
    console.print(
        f"  Custo total ({remaining:,} decisões): [green]${remaining * 0.000015:.2f}[/green]\n",
    )

    # Processar em lote
    batch_size = min(100, remaining)

    console.print(f"[yellow]Processando primeiro lote de {batch_size} decisões...[/yellow]\n")

    # Buscar decisões não analisadas
    unanalyzed = conn.execute(f"""
        SELECT i.id, i.texto
        FROM intimations i
        LEFT JOIN analysis_results ar ON i.id = ar.intimation_id
        WHERE ar.intimation_id IS NULL
          AND i.texto IS NOT NULL
          AND LENGTH(i.texto) > 100
        ORDER BY i.id
        LIMIT {batch_size}
    """).fetchall()

    console.print(f"✓ Carregadas {len(unanalyzed)} decisões para processar\n")

    # Processar
    results = []
    outcome_counts = Counter()

    for intimation_id, texto in track(unanalyzed, description="Classificando"):
        try:
            prediction = classify_with_knn(texto, table, k=5)

            results.append(
                {
                    "intimation_id": intimation_id,
                    "outcome": prediction["outcome"],
                    "confidence": prediction["confidence"],
                    "votes": prediction["votes"],
                },
            )

            outcome_counts[prediction["outcome"]] += 1

        except (duckdb.Error, KeyError, ValueError, TypeError) as e:
            console.print(f"[red]Erro no ID {intimation_id}: {e}[/red]")
            continue

    # Mostrar resultados
    console.print(f"\n[bold green]✓ Processadas {len(results)} decisões[/bold green]\n")

    dist_table = Table(title="Distribuição de Resultados")
    dist_table.add_column("Outcome", style="cyan")
    dist_table.add_column("Count", style="yellow")
    dist_table.add_column("Percentage", style="green")

    for outcome, count in outcome_counts.most_common():
        pct = (count / len(results)) * 100
        dist_table.add_row(outcome, str(count), f"{pct:.1f}%")

    console.print(dist_table)

    # Mostrar amostras
    console.print("\n[bold]Amostras de Classificações:[/bold]\n")
    for i, r in enumerate(results[:5], 1):
        console.print(f"{i}. ID {r['intimation_id']}")
        console.print(f"   Outcome: [cyan]{r['outcome']}[/cyan] (confiança: {r['confidence']:.2f})")
        console.print(f"   Votos: {r['votes']}\n")

    # Salvar no banco?
    console.print("[bold yellow]Próximo passo:[/bold yellow]")
    console.print("  Estes resultados podem ser salvos em uma tabela 'rag_classifications'")
    console.print("  para análise posterior e comparação com LLM.\n")

    # Criar tabela se não existir
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_classifications (
            intimation_id BIGINT PRIMARY KEY,
            outcome VARCHAR NOT NULL,
            confidence_score DOUBLE NOT NULL,
            votes_json VARCHAR,
            classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Inserir resultados
    console.print("[yellow]Salvando resultados no banco...[/yellow]")
    for r in results:
        conn.execute(
            """
            INSERT OR REPLACE INTO rag_classifications
            (intimation_id, outcome, confidence_score, votes_json)
            VALUES (?, ?, ?, ?)
        """,
            (r["intimation_id"], r["outcome"], r["confidence"], json.dumps(r["votes"])),
        )

    conn.commit()
    console.print("[green]✓ Resultados salvos em 'rag_classifications'[/green]\n")

    # Estatísticas finais
    total_classified = conn.execute("SELECT COUNT(*) FROM rag_classifications").fetchone()[0]
    console.print(f"[bold]Total de decisões classificadas por RAG: {total_classified:,}[/bold]\n")

    conn.close()


if __name__ == "__main__":
    main()
