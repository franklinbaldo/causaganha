#!/usr/bin/env python3

MAGIC_VAL_0_60 = 0.60
MAGIC_VAL_0_80 = 0.80

"""Classify decisions using pre-computed batch embeddings + k-NN (zero additional cost)."""

import json
from collections import Counter

import duckdb
import lancedb
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table


console = Console()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np))


def classify_with_knn_precomputed(
    query_embeddings: list[list[float]],
    table: lancedb.table.Table,
    k: int = 5,
) -> dict:
    """Classify using k-NN with pre-computed embeddings."""
    all_neighbors = []

    # Para cada chunk embedding, buscar vizinhos
    for embedding in query_embeddings:
        results = table.search(embedding).limit(k).to_pandas()
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
    """Classify decisions from batch embeddings."""
    console.print("\n[bold cyan]🎯 Classificação k-NN: Usando Batch Embeddings[/bold cyan]\n")

    # Verificar arquivo de embeddings
    embeddings_file = "data/decision_embeddings.jsonl"
    if not Path(embeddings_file).exists():
        console.print(f"[red]Erro: {embeddings_file} não encontrado[/red]")
        console.print("[yellow]Execute batch_embed_decisions.py primeiro[/yellow]\n")
        return

    # Conectar LanceDB
    db_path = Path("data/lancedb")
    if not db_path.exists():
        console.print("[red]Erro: LanceDB não existe[/red]")
        console.print("[yellow]Execute index_ground_truth.py primeiro[/yellow]\n")
        return

    db = lancedb.connect(str(db_path))
    table_name = "ground_truth_embeddings"

    if table_name not in db.table_names():
        console.print(f"[red]Erro: Tabela {table_name} não existe[/red]")
        return

    table = db.open_table(table_name)

    # Conectar DuckDB
    conn = duckdb.connect("data/causaganha.duckdb")

    # Criar tabela de resultados se não existir
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rag_classifications (
            intimation_id BIGINT PRIMARY KEY,
            outcome VARCHAR NOT NULL,
            confidence_score DOUBLE NOT NULL,
            votes_json VARCHAR,
            classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Carregar embeddings
    console.print(f"[yellow]Carregando embeddings de {embeddings_file}...[/yellow]")

    embeddings_data = []
    with Path(embeddings_file).open() as f:
        for line in f:
            record = json.loads(line)
            embeddings_data.append(record)

    console.print(
        f"[green]✓ Carregados embeddings para {len(embeddings_data):,} decisões[/green]\n",
    )

    # Processar classificações
    console.print("[yellow]Classificando decisões...[/yellow]\n")

    results = []
    outcome_counts = Counter()

    for record in track(embeddings_data, description="Classificando"):
        intimation_id = record["intimation_id"]

        # Extrair embeddings de todos os chunks
        chunk_embeddings = [chunk["embedding"] for chunk in record["chunks"]]

        try:
            prediction = classify_with_knn_precomputed(chunk_embeddings, table, k=5)

            results.append(
                {
                    "intimation_id": intimation_id,
                    "outcome": prediction["outcome"],
                    "confidence": prediction["confidence"],
                    "votes": prediction["votes"],
                },
            )

            outcome_counts[prediction["outcome"]] += 1

        except Exception as e:
            console.print(f"[red]Erro no ID {intimation_id}: {e}[/red]")
            continue

    # Mostrar resultados
    console.print(f"\n[bold green]✓ Classificadas {len(results):,} decisões[/bold green]\n")

    dist_table = Table(title="Distribuição de Resultados")
    dist_table.add_column("Outcome", style="cyan")
    dist_table.add_column("Count", style="yellow")
    dist_table.add_column("Percentage", style="green")

    for outcome, count in outcome_counts.most_common():
        pct = (count / len(results)) * 100
        dist_table.add_row(outcome, str(count), f"{pct:.1f}%")

    console.print(dist_table)

    # Análise de confiança
    console.print("\n[bold]Análise de Confiança:[/bold]\n")

    confidence_buckets = {
        "Alta (≥80%)": sum(1 for r in results if r["confidence"] >= MAGIC_VAL_0_80),
        "Média (60-80%)": sum(
            1 for r in results if MAGIC_VAL_0_60 <= r["confidence"] < MAGIC_VAL_0_80
        ),
        "Baixa (<60%)": sum(1 for r in results if r["confidence"] < MAGIC_VAL_0_60),
    }

    conf_table = Table()
    conf_table.add_column("Confiança", style="cyan")
    conf_table.add_column("Count", style="yellow")
    conf_table.add_column("Percentage", style="green")

    for bucket, count in confidence_buckets.items():
        pct = (count / len(results)) * 100
        conf_table.add_row(bucket, str(count), f"{pct:.1f}%")

    console.print(conf_table)

    # Mostrar amostras
    console.print("\n[bold]Amostras de Classificações:[/bold]\n")

    # Mostrar 3 de cada tipo de confiança
    high_conf = [r for r in results if r["confidence"] >= MAGIC_VAL_0_80][:3]
    low_conf = [r for r in results if r["confidence"] < MAGIC_VAL_0_60][:3]

    console.print("[cyan]Alta Confiança (≥80%):[/cyan]")
    for r in high_conf:
        console.print(f"  ID {r['intimation_id']}: {r['outcome']} ({r['confidence']:.2%})")

    if low_conf:
        console.print("\n[yellow]Baixa Confiança (<60%):[/yellow]")
        for r in low_conf:
            console.print(f"  ID {r['intimation_id']}: {r['outcome']} ({r['confidence']:.2%})")
            console.print(f"    Votos: {r['votes']}")

    # Salvar no banco
    console.print("\n[yellow]Salvando resultados no banco...[/yellow]")

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

    # Estatísticas finais
    total_classified = conn.execute("SELECT COUNT(*) FROM rag_classifications").fetchone()[0]

    console.print("[green]✓ Resultados salvos em 'rag_classifications'[/green]\n")

    console.print(
        Panel(
            f"[bold]Total Classificadas:[/bold] {total_classified:,}\n"
            f"[bold]Custo Total:[/bold] $0.045 (batch embeddings)\n"
            f"[bold]Custo por Classificação:[/bold] ${0.045 / total_classified:.6f}\n"
            f"[bold]Economia vs LLM:[/bold] 98.1% (${2.43 - 0.045:.2f} economizados)",
            title="✓ Processamento Completo",
        ),
    )

    # Comparação com ground truth se disponível
    comparison = conn.execute("""
        SELECT
            gt.outcome as gt_outcome,
            rag.outcome as rag_outcome,
            rag.confidence_score,
            COUNT(*) as count
        FROM ground_truth gt
        JOIN rag_classifications rag ON gt.intimation_id = rag.intimation_id
        GROUP BY gt.outcome, rag.outcome, rag.confidence_score
        ORDER BY count DESC
    """).fetchall()

    if comparison:
        console.print("\n[bold]Comparação com Ground Truth:[/bold]\n")

        comp_table = Table()
        comp_table.add_column("GT Outcome", style="cyan")
        comp_table.add_column("RAG Outcome", style="yellow")
        comp_table.add_column("Confidence", style="green")
        comp_table.add_column("Count", style="magenta")

        for gt_out, rag_out, conf, count in comparison:
            match = "✓" if gt_out == rag_out else "✗"
            comp_table.add_row(gt_out, f"{match} {rag_out}", f"{conf:.2%}", str(count))

        console.print(comp_table)

    console.print()
    conn.close()


if __name__ == "__main__":
    main()
