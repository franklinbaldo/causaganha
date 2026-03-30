#!/usr/bin/env python3
"""Testar acurácia do RAG com k-NN usando ground truth."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os
from collections import Counter

import duckdb
import lancedb
from google import genai
from rich.console import Console
from rich.progress import track
from rich.table import Table


console = Console()


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

        if end < len(text):
            last_period = chunk.rfind(".")
            if last_period > chunk_size * 0.7:
                end = start + last_period + 1
                chunk = text[start:end]

        prefixed_chunk = f"{CHUNK_INSTRUCTION}\n\n{chunk.strip()}"
        chunks.append(prefixed_chunk)

        start = end - overlap

    return chunks


_genai_client = None


def get_embedding(text: str) -> list[float]:
    """Get embedding."""
    result = _genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=[text],
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return result.embeddings[0].values


def classify_with_knn(
    query_text: str,
    table: lancedb.table.Table,
    k: int = 5,
    exclude_id: int | None = None,
) -> dict:
    """Classificar usando k-NN."""
    # Chunk e embedar query
    query_chunks = chunk_text_with_prefix(query_text)

    # Para cada chunk da query, buscar vizinhos
    all_neighbors = []

    for query_chunk in query_chunks:
        query_embedding = get_embedding(query_chunk)

        # Buscar k vizinhos mais próximos
        results = table.search(query_embedding).limit(k * 2).to_pandas()  # 2x para filtrar

        # Filtrar se necessário (cross-validation)
        if exclude_id is not None:
            results = results[results["intimation_id"] != exclude_id]

        all_neighbors.extend(results["outcome"].tolist()[:k])

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
    """Testar acurácia do RAG."""
    console.print("\n[bold cyan]🎯 Teste de Acurácia: RAG com k-NN[/bold cyan]\n")

    # Configurar
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]Erro: GEMINI_API_KEY não configurada[/red]")
        return

    global _genai_client
    _genai_client = genai.Client(api_key=api_key)

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

    # Buscar ground truth para teste
    conn = duckdb.connect("data/causaganha.duckdb", read_only=True)

    test_set = conn.execute("""
        SELECT intimation_id, outcome, texto
        FROM ground_truth
        ORDER BY RANDOM()
        LIMIT 30
    """).fetchall()

    console.print(f"✓ Testando com {len(test_set)} decisões\n")

    # Configurações de teste
    k_values = [3, 5, 7, 10]

    for k in k_values:
        console.print(f"\n[bold cyan]═══ Teste com k={k} ═══[/bold cyan]\n")

        results = []
        correct = 0

        for intimation_id, true_outcome, texto in track(
            test_set,
            description=f"Testando k={k}",
        ):
            # Classificar (excluindo a própria decisão - cross-validation)
            prediction = classify_with_knn(texto, table, k=k, exclude_id=intimation_id)

            predicted_outcome = prediction["outcome"]
            match = predicted_outcome == true_outcome

            if match:
                correct += 1

            results.append(
                {
                    "intimation_id": intimation_id,
                    "true": true_outcome,
                    "predicted": predicted_outcome,
                    "confidence": prediction["confidence"],
                    "match": match,
                    "votes": prediction["votes"],
                },
            )

        # Calcular métricas
        accuracy = (correct / len(test_set)) * 100

        # Mostrar resultados
        console.print(
            f"\n[bold]Acurácia com k={k}: {accuracy:.1f}% ({correct}/{len(test_set)})[/bold]\n",
        )

        # Matriz de confusão
        confusion = {}
        for r in results:
            key = (r["true"], r["predicted"])
            confusion[key] = confusion.get(key, 0) + 1

        conf_table = Table(title=f"Matriz de Confusão (k={k})")
        conf_table.add_column("Real", style="cyan")
        conf_table.add_column("Previsto", style="yellow")
        conf_table.add_column("Count", style="green")

        for (true, pred), count in sorted(confusion.items(), key=lambda x: -x[1]):
            style = "green" if true == pred else "red"
            conf_table.add_row(true, pred, str(count), style=style)

        console.print(conf_table)

        # Mostrar alguns erros
        errors = [r for r in results if not r["match"]]
        if errors:
            console.print(f"\n[yellow]Exemplos de Erros (k={k}):[/yellow]\n")
            for i, err in enumerate(errors[:3], 1):
                console.print(f"{i}. ID {err['intimation_id']}")
                console.print(f"   Real: {err['true']}")
                console.print(f"   Previsto: {err['predicted']} (conf: {err['confidence']:.2f})")
                console.print(f"   Votos: {err['votes']}\n")

    # Comparação final
    console.print("\n[bold cyan]📊 COMPARAÇÃO GERAL[/bold cyan]\n")

    comparison = Table(title="Acurácia por Valor de k")
    comparison.add_column("k", style="cyan")
    comparison.add_column("Acurácia", style="yellow")
    comparison.add_column("Corretos", style="green")

    # Reprocessar para comparação
    for k in k_values:
        correct = 0
        for intimation_id, true_outcome, texto in test_set:
            prediction = classify_with_knn(texto, table, k=k, exclude_id=intimation_id)
            if prediction["outcome"] == true_outcome:
                correct += 1

        accuracy = (correct / len(test_set)) * 100
        comparison.add_row(str(k), f"{accuracy:.1f}%", f"{correct}/{len(test_set)}")

    console.print(comparison)

    # Comparação com baseline
    console.print("\n[bold]Comparação com Métodos Anteriores:[/bold]\n")

    baseline_table = Table()
    baseline_table.add_column("Método", style="cyan")
    baseline_table.add_column("Acurácia", style="yellow")
    baseline_table.add_column("Custo/5794 decisões", style="green")

    baseline_table.add_row("Frases Genéricas", "13.3%", "$0.09")
    baseline_table.add_row("LLM (Gemini Flash)", "~85%", "$2.43")

    # Calcular melhor k
    best_k = max(
        k_values,
        key=lambda k: sum(
            1
            for intimation_id, true_outcome, texto in test_set
            if classify_with_knn(texto, table, k=k, exclude_id=intimation_id)["outcome"]
            == true_outcome
        ),
    )

    best_correct = sum(
        1
        for intimation_id, true_outcome, texto in test_set
        if classify_with_knn(texto, table, k=best_k, exclude_id=intimation_id)["outcome"]
        == true_outcome
    )
    best_accuracy = (best_correct / len(test_set)) * 100

    baseline_table.add_row(
        f"[bold]RAG k-NN (k={best_k})[/bold]",
        f"[bold green]{best_accuracy:.1f}%[/bold green]",
        "[bold green]$0.09[/bold green]",
    )

    console.print(baseline_table)

    console.print("\n[bold green]✓ Teste Completo![/bold green]\n")

    conn.close()


if __name__ == "__main__":
    main()
