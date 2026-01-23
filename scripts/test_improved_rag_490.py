#!/usr/bin/env python3
"""Test improved RAG accuracy on 490 aggregated outcome labels.

This script tests the improved RAG analyzer on the 490 usable documents
(WIN/LOSS/PARTIAL) from the 10-agent labeling task.
"""

import asyncio
import json
import sys
from pathlib import Path

import duckdb
import structlog
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.config import settings
from causaganha.v2.analysis.embedding_service import EmbeddingService
from causaganha.v2.analysis.improved_rag_analyzer import ImprovedRAGAnalyzer
from causaganha.v2.analysis.parquet_party_loader import ParquetPartyLoader

console = Console()
logger = structlog.get_logger()


def normalize_outcome(outcome: str) -> str:
    """Normalize outcome to WIN/LOSS/PARTIAL."""
    outcome_upper = outcome.upper().strip()
    if outcome_upper in ["WIN", "LOSS", "PARTIAL"]:
        return outcome_upper
    return "UNKNOWN"


async def test_improved_rag():
    """Test improved RAG on 490 aggregated labels."""
    console.print("\n[cyan]Testing Improved RAG on 490 Documents[/cyan]\n")
    console.print("=" * 70)

    # Load aggregated labels
    labels_file = settings.DATA_DIR / "outcome_labels_aggregated.json"
    console.print(f"📂 Loading labels: {labels_file}")

    with open(labels_file) as f:
        data = json.load(f)

    all_docs = data["documents"]

    # Filter to usable docs (not UNKNOWN)
    testable_docs = [
        doc for doc in all_docs
        if doc.get("outcome_normalized") in ["WIN", "LOSS", "PARTIAL"]
    ]

    console.print(f"✓ Loaded {len(all_docs)} total documents")
    console.print(f"✓ Testable (not UNKNOWN): {len(testable_docs)} documents\n")

    # Initialize components
    console.print("🔧 Initializing components...")

    # Embedding service (local model)
    service = await EmbeddingService.create(provider="local")
    console.print(f"  ✓ Embedding: {service.model.name} ({service.model.dimension}D)")

    # Party loader
    parquet_dir = settings.DATA_DIR / "ia_cache" / "djen-parquet-2026-01-21-TRF4"
    party_loader = ParquetPartyLoader(parquet_dir)
    console.print(f"  ✓ Party loader: {parquet_dir.name}")

    # Improved RAG analyzer
    analyzer = ImprovedRAGAnalyzer(
        embedding_service=service,
        party_loader=party_loader,
    )
    console.print(f"  ✓ Improved RAG with chunking\n")

    # Connect to database
    db_path = settings.DATA_DIR / "causaganha_real.duckdb"
    db = duckdb.connect(str(db_path), read_only=True)

    # Test each document
    console.print(f"🧪 Testing {len(testable_docs)} documents...\n")

    results = []
    correct = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing...", total=len(testable_docs))

        for i, doc in enumerate(testable_docs, 1):
            intimation_id = doc["intimation_id"]
            actual_outcome = normalize_outcome(doc["outcome_normalized"])

            # Get texto from database
            result = db.execute(
                "SELECT texto FROM intimations WHERE id = ?",
                [intimation_id],
            ).fetchone()

            if not result or not result[0]:
                logger.warning("texto_not_found", intimation_id=intimation_id)
                continue

            texto = result[0]

            # Run improved RAG
            try:
                prediction = await analyzer.analyze(intimation_id, texto)
                predicted_outcome = normalize_outcome(prediction.outcome)
            except Exception as e:
                logger.error("analysis_failed", intimation_id=intimation_id, error=str(e))
                predicted_outcome = "UNKNOWN"

            # Check correctness
            is_correct = predicted_outcome == actual_outcome
            if is_correct:
                correct += 1

            results.append({
                "intimation_id": intimation_id,
                "numero_processo": doc.get("numero_processo"),
                "actual_outcome": actual_outcome,
                "predicted_outcome": predicted_outcome,
                "correct": is_correct,
            })

            # Update progress
            progress.update(
                task,
                advance=1,
                description=f"[{i}/{len(testable_docs)}] Correct: {correct}/{i} ({correct/i*100:.1f}%)",
            )

    db.close()

    # Calculate final accuracy
    total = len(results)
    accuracy = correct / total if total > 0 else 0

    # Print results
    console.print("\n" + "=" * 70)
    console.print("[bold green]RESULTS[/bold green]\n")

    console.print(f"Total tested:     {total}")
    console.print(f"Correct:          {correct}")
    console.print(f"Incorrect:        {total - correct}")
    console.print(f"[bold]Accuracy:         {accuracy:.1%}[/bold]\n")

    # Confusion matrix
    confusion = {"WIN": {"WIN": 0, "LOSS": 0, "PARTIAL": 0},
                 "LOSS": {"WIN": 0, "LOSS": 0, "PARTIAL": 0},
                 "PARTIAL": {"WIN": 0, "LOSS": 0, "PARTIAL": 0}}

    for r in results:
        actual = r["actual_outcome"]
        predicted = r["predicted_outcome"]
        if predicted != "UNKNOWN":
            confusion[actual][predicted] += 1

    console.print("Confusion Matrix:")
    console.print("                Predicted")
    console.print("         WIN    LOSS  PARTIAL")
    for actual in ["WIN", "LOSS", "PARTIAL"]:
        console.print(
            f"{actual:8s} {confusion[actual]['WIN']:3d}    "
            f"{confusion[actual]['LOSS']:3d}    {confusion[actual]['PARTIAL']:3d}"
        )

    console.print("\n" + "=" * 70)

    # Save results
    output = {
        "method": "ImprovedRAG",
        "provider": "local",
        "model": service.model.name,
        "dimension": service.model.dimension,
        "total_tested": total,
        "correct": correct,
        "accuracy": accuracy,
        "predictions": results,
    }

    output_file = settings.DATA_DIR / "improved_rag_490_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    console.print(f"💾 Results saved to: {output_file}\n")

    # Compare to baseline
    console.print("📊 Comparison to Baselines:\n")
    console.print(f"  Situation Classifier (18 docs): 72.2%")
    console.print(f"  Improved RAG (18 docs):         55.6%")
    console.print(f"  [bold]Improved RAG (490 docs):        {accuracy:.1%}[/bold]")

    if accuracy > 0.70:
        console.print("\n✅ [green]Excellent! RAG improved with larger dataset[/green]")
    elif accuracy > 0.60:
        console.print("\n✓ [yellow]Good accuracy, but situation classifier still better[/yellow]")
    else:
        console.print("\n⚠️  [red]Low accuracy - embedding model likely insufficient[/red]")

    console.print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_improved_rag())
