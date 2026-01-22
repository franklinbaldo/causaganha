#!/usr/bin/env python3
"""Winner/Loser identification quality benchmark.

Tests the end-to-end accuracy of identifying which lawyer won and lost
in legal decisions. This is CausaGanha's core use case.

Usage:
    python scripts/benchmark_winner_loser_accuracy.py
    python scripts/benchmark_winner_loser_accuracy.py --providers local jina --sample-size 100
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import duckdb
import structlog
import typer
from rich.console import Console
from rich.table import Table

from causaganha.config import settings
from causaganha.v2.analysis.rag_analyzer import RAGAnalyzer


logger = structlog.get_logger()
console = Console()
app = typer.Typer()


@dataclass
class GroundTruthDecision:
    """Legal decision with known winner/loser (ground truth)."""

    intimation_id: int
    texto: str
    true_outcome: str  # Ground truth outcome
    true_winner_oab: str | None
    true_loser_oab: str | None
    decision_type: str | None


@dataclass
class AccuracyMetrics:
    """Metrics for winner/loser identification accuracy."""

    total_decisions: int
    outcome_accuracy: float  # % correctly classified outcome
    outcome_correct: int
    outcome_incorrect: int

    # Confusion matrix for outcomes
    procedente_correct: int
    procedente_missed: int
    improcedente_correct: int
    improcedente_missed: int
    parcial_correct: int
    parcial_missed: int

    avg_confidence: float  # Average confidence score
    high_confidence_accuracy: float  # Accuracy when confidence > 0.7


class WinnerLoserBenchmark:
    """Benchmark winner/loser identification accuracy."""

    def __init__(self, db_path: str | Path):
        """Initialize benchmark.

        Args:
            db_path: Path to DuckDB database with analyzed decisions.
        """
        self.db_path = Path(db_path)
        self.decisions: list[GroundTruthDecision] = []

    def load_ground_truth(self, sample_size: int = 100) -> None:
        """Load decisions with known outcomes (ground truth).

        Args:
            sample_size: Number of decisions to load.
        """
        console.print(f"\n[cyan]Loading {sample_size} decisions with ground truth...[/cyan]")

        conn = duckdb.connect(str(self.db_path), read_only=True)

        # Query analyzed decisions with known outcomes
        query = """
        SELECT
            i.id,
            i.texto,
            da.outcome,
            da.winner_lawyer_oab,
            da.loser_lawyer_oab,
            da.decision_type
        FROM intimations i
        INNER JOIN decision_analysis da ON i.id = da.intimation_id
        WHERE i.texto IS NOT NULL
          AND LENGTH(i.texto) > 100
          AND da.outcome IS NOT NULL
          AND da.outcome != 'unknown'
        ORDER BY RANDOM()
        LIMIT ?
        """

        results = conn.execute(query, [sample_size]).fetchall()
        conn.close()

        for row in results:
            decision = GroundTruthDecision(
                intimation_id=row[0],
                texto=row[1],
                true_outcome=row[2],
                true_winner_oab=row[3],
                true_loser_oab=row[4],
                decision_type=row[5],
            )
            self.decisions.append(decision)

        console.print(f"  ✓ Loaded {len(self.decisions)} decisions with ground truth")

        # Show outcome distribution
        outcome_counts = {}
        for d in self.decisions:
            outcome = self._normalize_outcome(d.true_outcome)
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        console.print("  • Outcome distribution:")
        for outcome, count in sorted(outcome_counts.items()):
            console.print(f"    - {outcome}: {count}")

    def _normalize_outcome(self, outcome: str) -> str:
        """Normalize outcome string for comparison.

        Args:
            outcome: Raw outcome string.

        Returns:
            Normalized outcome (WIN, LOSS, PARTIAL, UNKNOWN).
        """
        outcome_lower = outcome.lower()

        if "procedente" in outcome_lower and "parcial" not in outcome_lower:
            return "WIN"
        elif "improcedente" in outcome_lower:
            return "LOSS"
        elif "parcial" in outcome_lower:
            return "PARTIAL"
        elif "provido" in outcome_lower and "improvido" not in outcome_lower:
            return "WIN"
        elif "improvido" in outcome_lower or "nego" in outcome_lower:
            return "LOSS"
        else:
            return "UNKNOWN"

    async def evaluate_provider(
        self,
        provider_name: str,
        rag_analyzer: RAGAnalyzer,
    ) -> AccuracyMetrics:
        """Evaluate outcome classification accuracy for a provider.

        Args:
            provider_name: Name of embedding provider.
            rag_analyzer: RAG analyzer using this provider's embeddings.

        Returns:
            AccuracyMetrics with accuracy results.
        """
        console.print(f"\n[cyan]Evaluating {provider_name} on winner/loser identification...[/cyan]")

        outcome_correct = 0
        outcome_incorrect = 0
        confidences = []

        # Confusion matrix counters
        confusion = {
            "WIN": {"correct": 0, "missed": 0},
            "LOSS": {"correct": 0, "missed": 0},
            "PARTIAL": {"correct": 0, "missed": 0},
        }

        high_confidence_correct = 0
        high_confidence_total = 0

        for i, decision in enumerate(self.decisions):
            if (i + 1) % 20 == 0:
                console.print(f"  • Processed {i + 1}/{len(self.decisions)} decisions...")

            try:
                # Run RAG analysis
                result = await rag_analyzer.analyze_text(
                    decision.texto,
                    intimation_id=decision.intimation_id,
                )

                # Normalize both outcomes for comparison
                true_outcome = self._normalize_outcome(decision.true_outcome)
                predicted_outcome = self._normalize_outcome(result.outcome)

                # Check if outcome is correct
                is_correct = true_outcome == predicted_outcome

                if is_correct:
                    outcome_correct += 1
                    confusion[true_outcome]["correct"] += 1
                else:
                    outcome_incorrect += 1
                    confusion[true_outcome]["missed"] += 1

                # Track confidence
                if result.rag_confidence:
                    confidences.append(result.rag_confidence)

                    # Track high confidence accuracy
                    if result.rag_confidence >= 0.7:
                        high_confidence_total += 1
                        if is_correct:
                            high_confidence_correct += 1

            except Exception as e:
                logger.exception(
                    "evaluation_failed",
                    intimation_id=decision.intimation_id,
                    error=str(e),
                )
                outcome_incorrect += 1
                confusion[self._normalize_outcome(decision.true_outcome)]["missed"] += 1

        # Calculate metrics
        total = len(self.decisions)
        outcome_accuracy = outcome_correct / total if total > 0 else 0.0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        high_conf_accuracy = (
            high_confidence_correct / high_confidence_total
            if high_confidence_total > 0
            else 0.0
        )

        metrics = AccuracyMetrics(
            total_decisions=total,
            outcome_accuracy=outcome_accuracy,
            outcome_correct=outcome_correct,
            outcome_incorrect=outcome_incorrect,
            procedente_correct=confusion["WIN"]["correct"],
            procedente_missed=confusion["WIN"]["missed"],
            improcedente_correct=confusion["LOSS"]["correct"],
            improcedente_missed=confusion["LOSS"]["missed"],
            parcial_correct=confusion["PARTIAL"]["correct"],
            parcial_missed=confusion["PARTIAL"]["missed"],
            avg_confidence=avg_confidence,
            high_confidence_accuracy=high_conf_accuracy,
        )

        console.print(f"\n  ✓ Evaluation complete for {provider_name}")
        console.print(f"    • Outcome Accuracy: {metrics.outcome_accuracy:.2%}")
        console.print(f"    • Avg Confidence: {metrics.avg_confidence:.3f}")
        console.print(f"    • High Confidence Accuracy (>0.7): {metrics.high_confidence_accuracy:.2%}")

        return metrics


def print_comparison_table(results: dict[str, AccuracyMetrics]) -> None:
    """Print comparison table of provider accuracies.

    Args:
        results: Dict mapping provider name to AccuracyMetrics.
    """
    table = Table(
        title="Winner/Loser Identification Accuracy by Provider",
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Provider", style="cyan")
    table.add_column("Total", justify="right", style="white")
    table.add_column("Accuracy", justify="right", style="green")
    table.add_column("Correct", justify="right", style="green")
    table.add_column("Wrong", justify="right", style="red")
    table.add_column("Avg Conf", justify="right", style="yellow")
    table.add_column("High Conf Acc", justify="right", style="blue")

    for provider, metrics in results.items():
        table.add_row(
            provider.upper(),
            str(metrics.total_decisions),
            f"{metrics.outcome_accuracy:.1%}",
            str(metrics.outcome_correct),
            str(metrics.outcome_incorrect),
            f"{metrics.avg_confidence:.3f}",
            f"{metrics.high_confidence_accuracy:.1%}",
        )

    console.print("\n")
    console.print(table)


def print_confusion_matrix(provider: str, metrics: AccuracyMetrics) -> None:
    """Print confusion matrix for a provider.

    Args:
        provider: Provider name.
        metrics: AccuracyMetrics with confusion data.
    """
    console.print(f"\n[bold cyan]Confusion Matrix - {provider.upper()}[/bold cyan]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("True Outcome", style="cyan")
    table.add_column("Correct", justify="right", style="green")
    table.add_column("Missed", justify="right", style="red")
    table.add_column("Accuracy", justify="right", style="yellow")

    outcomes = [
        ("WIN (Procedente)", metrics.procedente_correct, metrics.procedente_missed),
        ("LOSS (Improcedente)", metrics.improcedente_correct, metrics.improcedente_missed),
        ("PARTIAL (Parcial)", metrics.parcial_correct, metrics.parcial_missed),
    ]

    for outcome_name, correct, missed in outcomes:
        total = correct + missed
        accuracy = correct / total if total > 0 else 0.0
        table.add_row(
            outcome_name,
            str(correct),
            str(missed),
            f"{accuracy:.1%}",
        )

    console.print(table)


def print_recommendations(results: dict[str, AccuracyMetrics]) -> None:
    """Print recommendations based on accuracy results.

    Args:
        results: Dict mapping provider name to AccuracyMetrics.
    """
    console.print("\n[bold green]Recommendations:[/bold green]\n")

    # Find best provider
    best_provider = max(results.items(), key=lambda x: x[1].outcome_accuracy)
    best_name, best_metrics = best_provider

    console.print(f"🏆 Best Provider: [bold]{best_name.upper()}[/bold]")
    console.print(f"   • Accuracy: {best_metrics.outcome_accuracy:.1%}")
    console.print(f"   • Confidence: {best_metrics.avg_confidence:.3f}")

    # Quality thresholds
    console.print("\n[bold cyan]Quality Assessment:[/bold cyan]")
    for provider, metrics in results.items():
        if metrics.outcome_accuracy >= 0.80:
            console.print(f"  ✅ {provider.upper()}: Excellent ({metrics.outcome_accuracy:.1%}) - Production ready")
        elif metrics.outcome_accuracy >= 0.70:
            console.print(f"  ⚠️  {provider.upper()}: Good ({metrics.outcome_accuracy:.1%}) - Acceptable")
        elif metrics.outcome_accuracy >= 0.60:
            console.print(f"  ⚠️  {provider.upper()}: Fair ({metrics.outcome_accuracy:.1%}) - Needs improvement")
        else:
            console.print(f"  ❌ {provider.upper()}: Poor ({metrics.outcome_accuracy:.1%}) - Not recommended")

    console.print("\n[bold cyan]Key Insights:[/bold cyan]")
    console.print("  • Accuracy >80%: Excellent - Can confidently identify winners/losers")
    console.print("  • Accuracy 70-80%: Good - Usable with human review on edge cases")
    console.print("  • Accuracy <70%: Needs improvement - Consider better models or more training data")


@app.command()
def main(
    providers: list[str] = typer.Option(
        ["local"],
        "--providers",
        "-p",
        help="Providers to benchmark",
    ),
    sample_size: int = typer.Option(
        100,
        "--sample-size",
        "-n",
        help="Number of decisions to test",
    ),
    db_path: str = typer.Option(
        str(settings.DB_PATH),
        "--db",
        help="Path to DuckDB database",
    ),
) -> None:
    """Benchmark winner/loser identification accuracy.

    Tests how accurately each embedding provider helps identify
    which lawyer won and which lost in legal decisions.
    """
    console.print("[bold]Winner/Loser Identification Accuracy Benchmark[/bold]")
    console.print(f"Database: {db_path}")
    console.print(f"Providers: {', '.join(providers)}")
    console.print(f"Sample size: {sample_size} decisions\n")

    try:
        # Initialize benchmark
        benchmark = WinnerLoserBenchmark(db_path)
        benchmark.load_ground_truth(sample_size)

        if not benchmark.decisions:
            console.print("[red]Error: No decisions with ground truth found in database.[/red]")
            console.print("\n[yellow]Tip: Run data collection pipeline first, or use test data:[/yellow]")
            console.print("  uv run python scripts/generate_test_legal_data.py 200")
            console.print(f"  uv run python scripts/benchmark_winner_loser_accuracy.py --db data/causaganha_test.duckdb")
            raise typer.Exit(1)

        # Evaluate each provider
        results = {}

        async def run_evaluations():
            for provider in providers:
                try:
                    console.print(f"\n[cyan]Initializing {provider} RAG analyzer...[/cyan]")
                    rag_analyzer = await RAGAnalyzer.create()

                    metrics = await benchmark.evaluate_provider(provider, rag_analyzer)
                    results[provider] = metrics

                    # Print confusion matrix for this provider
                    print_confusion_matrix(provider, metrics)

                except Exception as e:
                    console.print(f"[red]Failed to evaluate {provider}: {e}[/red]")
                    logger.exception("provider_evaluation_failed", provider=provider)

        asyncio.run(run_evaluations())

        if results:
            print_comparison_table(results)
            print_recommendations(results)

            # Export results
            import json

            output_file = Path("data/winner_loser_accuracy_results.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)

            export_data = {
                provider: {
                    "total_decisions": m.total_decisions,
                    "outcome_accuracy": m.outcome_accuracy,
                    "outcome_correct": m.outcome_correct,
                    "outcome_incorrect": m.outcome_incorrect,
                    "avg_confidence": m.avg_confidence,
                    "high_confidence_accuracy": m.high_confidence_accuracy,
                    "confusion_matrix": {
                        "procedente": {
                            "correct": m.procedente_correct,
                            "missed": m.procedente_missed,
                        },
                        "improcedente": {
                            "correct": m.improcedente_correct,
                            "missed": m.improcedente_missed,
                        },
                        "parcial": {
                            "correct": m.parcial_correct,
                            "missed": m.parcial_missed,
                        },
                    },
                }
                for provider, m in results.items()
            }

            with output_file.open("w") as f:
                json.dump(export_data, f, indent=2)

            console.print(f"\n[green]Results exported to: {output_file}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Benchmark failed: {e}[/red]")
        logger.exception("benchmark_failed", error=str(e))
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
