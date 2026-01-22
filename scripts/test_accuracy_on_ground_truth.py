#!/usr/bin/env python3
"""Test embedding provider accuracy against manually-labeled ground truth.

This script loads real legal decisions with manually-labeled outcomes and tests
how accurately each embedding provider can identify winners and losers using RAG.

Usage:
    python scripts/test_accuracy_on_ground_truth.py
    python scripts/test_accuracy_on_ground_truth.py --providers local jina
    python scripts/test_accuracy_on_ground_truth.py --sample-size 10
"""

import asyncio
import json
from pathlib import Path

import duckdb
import structlog
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from causaganha.config import settings
from causaganha.v2.analysis.embedding_service import EmbeddingService
from causaganha.v2.analysis.heuristic_classifier import HeuristicClassifier
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer


logger = structlog.get_logger()
console = Console()
app = typer.Typer()


def normalize_outcome(outcome: str) -> str:
    """Normalize outcome to WIN/LOSS/PARTIAL."""
    outcome_lower = outcome.upper()
    if "PROCEDENTE" in outcome_lower and "PARCIAL" not in outcome_lower:
        return "WIN"
    elif "IMPROCEDENTE" in outcome_lower:
        return "LOSS"
    elif "PARCIAL" in outcome_lower:
        return "PARTIAL"
    else:
        return "UNKNOWN"


async def test_provider_accuracy(
    provider_name: str,
    ground_truth: list[dict],
    db_path: Path,
    use_heuristic: bool = False,
) -> dict:
    """Test accuracy of a single provider against ground truth.

    Args:
        provider_name: Name of embedding provider (local, jina, google)
        ground_truth: List of documents with manual labels
        db_path: Path to DuckDB database with real data

    Returns:
        Dict with accuracy metrics and predictions
    """
    method = "Heuristic" if use_heuristic else "RAG"
    console.print(f"\n[cyan]Testing provider: {provider_name} ({method})[/cyan]")

    # Initialize embedding service
    service = await EmbeddingService.create(provider=provider_name)
    console.print(f"  • Model: {service.model.name} ({service.model.dimension}D)")
    console.print(f"  • Method: {method}")

    # Initialize analyzer
    if use_heuristic:
        classifier = HeuristicClassifier(embedding_service=service)
    else:
        rag_analyzer = RAGAnalyzer(embedding_service=service)

    # Connect to database
    conn = duckdb.connect(str(db_path), read_only=True)

    results = []
    correct = 0
    total = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Analyzing {len(ground_truth)} documents...", total=len(ground_truth))

        for doc in ground_truth:
            # Skip UNKNOWN outcomes
            if doc['outcome'] == 'UNKNOWN':
                progress.advance(task)
                continue

            # Get full text from database
            intimation_id = doc['intimation_id']
            row = conn.execute(
                "SELECT texto FROM intimations WHERE id = ?",
                [int(intimation_id)]
            ).fetchone()

            if not row:
                logger.warning("document_not_found", intimation_id=intimation_id)
                progress.advance(task)
                continue

            texto = row[0]

            # Run analysis (RAG or Heuristic)
            try:
                if use_heuristic:
                    prediction = await classifier.predict(texto)
                    predicted_outcome = prediction.outcome
                else:
                    analysis = await rag_analyzer.analyze_text(texto)
                    predicted_outcome = normalize_outcome(analysis.outcome)
            except Exception as e:
                logger.error("analysis_failed", error=str(e), intimation_id=intimation_id, method=method)
                predicted_outcome = "ERROR"

            # Compare with ground truth
            actual_outcome = normalize_outcome(doc['outcome'])
            is_correct = predicted_outcome == actual_outcome

            if is_correct:
                correct += 1
            total += 1

            result = {
                "doc_id": doc['doc_id'],
                "intimation_id": intimation_id,
                "numero_processo": doc['numero_processo'],
                "actual_outcome": actual_outcome,
                "predicted_outcome": predicted_outcome,
                "correct": is_correct,
            }
            results.append(result)

            progress.advance(task)

    conn.close()

    accuracy = (correct / total * 100) if total > 0 else 0.0

    console.print(f"  ✓ Accuracy: {accuracy:.1f}% ({correct}/{total})")

    return {
        "provider": provider_name,
        "model": service.model.name,
        "dimension": service.model.dimension,
        "method": method,
        "total_tested": total,
        "correct": correct,
        "accuracy": accuracy,
        "predictions": results,
    }


@app.command()
def main(
    providers: list[str] = typer.Option(
        ["local"],
        "--provider",
        "-p",
        help="Embedding providers to test (local, jina, google)",
    ),
    use_heuristic: bool = typer.Option(
        False,
        "--heuristic",
        "-h",
        help="Use heuristic classifier instead of RAG",
    ),
    ground_truth_file: str = typer.Option(
        str(settings.DATA_DIR / "ground_truth_labels.json"),
        "--ground-truth",
        "-g",
        help="Path to ground truth labels JSON file",
    ),
    db_path: str = typer.Option(
        str(settings.DATA_DIR / "causaganha_real.duckdb"),
        "--db",
        "-d",
        help="Path to DuckDB database with real data",
    ),
    output_file: str = typer.Option(
        str(settings.DATA_DIR / "accuracy_results.json"),
        "--output",
        "-o",
        help="Path to save results",
    ),
) -> None:
    """Test embedding provider accuracy against manually-labeled ground truth."""

    console.print("[bold]Embedding Provider Accuracy Test on Ground Truth[/bold]")
    console.print(f"Ground truth: {ground_truth_file}")
    console.print(f"Database: {db_path}")
    console.print(f"Providers: {', '.join(providers)}\n")

    # Load ground truth
    with open(ground_truth_file, 'r') as f:
        data = json.load(f)

    ground_truth = data['documents']
    testable = [d for d in ground_truth if d['outcome'] != 'UNKNOWN']

    console.print(f"Total documents: {len(ground_truth)}")
    console.print(f"Testable (not UNKNOWN): {len(testable)}")

    # Count outcomes
    outcomes = {}
    for doc in testable:
        outcome = normalize_outcome(doc['outcome'])
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

    console.print("\nGround Truth Distribution:")
    for outcome, count in sorted(outcomes.items()):
        console.print(f"  {outcome}: {count}")

    # Test each provider
    async def run_tests():
        results = []
        for provider in providers:
            try:
                result = await test_provider_accuracy(
                    provider_name=provider,
                    ground_truth=testable,
                    db_path=Path(db_path),
                    use_heuristic=use_heuristic,
                )
                results.append(result)
            except Exception as e:
                console.print(f"[red]Error testing {provider}: {e}[/red]")
                logger.exception("provider_test_failed", provider=provider, error=str(e))

        return results

    results = asyncio.run(run_tests())

    # Display comparison table
    console.print("\n")
    table = Table(title="Accuracy Comparison on Ground Truth")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="blue")
    table.add_column("Method", style="magenta")
    table.add_column("Dimension", justify="right")
    table.add_column("Tested", justify="right")
    table.add_column("Correct", justify="right")
    table.add_column("Accuracy", justify="right", style="bold green")

    for result in results:
        table.add_row(
            result['provider'].upper(),
            result['model'],
            result['method'],
            str(result['dimension']),
            str(result['total_tested']),
            str(result['correct']),
            f"{result['accuracy']:.1f}%",
        )

    console.print(table)

    # Save results
    output_path = Path(output_file)
    with output_path.open('w') as f:
        json.dump({
            "ground_truth_file": ground_truth_file,
            "database": db_path,
            "total_documents": len(ground_truth),
            "testable_documents": len(testable),
            "outcome_distribution": outcomes,
            "results": results,
        }, f, indent=2)

    console.print(f"\n✓ Results saved to: {output_path}")


if __name__ == "__main__":
    app()
