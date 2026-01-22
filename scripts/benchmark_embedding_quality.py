#!/usr/bin/env python3
"""Quality benchmark for embedding providers using real legal documents.

Tests retrieval accuracy on actual CausaGanha legal data from PJe API.

Usage:
    python scripts/benchmark_embedding_quality.py
    python scripts/benchmark_embedding_quality.py --providers local jina --sample-size 200
"""

import asyncio
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import structlog
import typer
from rich.console import Console
from rich.table import Table

from causaganha.config import settings
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService


logger = structlog.get_logger()
console = Console()
app = typer.Typer()


@dataclass
class LegalDocument:
    """Legal document with metadata for testing."""

    id: int
    texto: str
    decision_type: str | None
    outcome: str | None
    nome_classe: str | None
    tipo_documento: str | None
    tribunal: str


@dataclass
class SearchQuery:
    """Search query with expected relevant document IDs."""

    query_text: str
    relevant_doc_ids: set[int]
    category: str  # Query category for analysis


@dataclass
class RetrievalMetrics:
    """Retrieval quality metrics."""

    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    ndcg_at_10: float
    mrr: float  # Mean Reciprocal Rank


class EmbeddingQualityBenchmark:
    """Benchmark embedding quality on real legal document retrieval."""

    def __init__(self, db_path: str | Path):
        """Initialize benchmark with database path.

        Args:
            db_path: Path to DuckDB database with legal documents.
        """
        self.db_path = Path(db_path)
        self.documents: list[LegalDocument] = []
        self.queries: list[SearchQuery] = []

    def load_documents(self, sample_size: int = 200) -> None:
        """Load sample of legal documents from database.

        Args:
            sample_size: Number of documents to load.
        """
        console.print(f"\n[cyan]Loading {sample_size} legal documents from database...[/cyan]")

        conn = duckdb.connect(str(self.db_path), read_only=True)

        # Query documents with meaningful text and metadata
        query = """
        SELECT DISTINCT
            i.id,
            i.texto,
            da.decision_type,
            da.outcome,
            i.nome_classe,
            i.tipo_documento,
            i.sigla_tribunal
        FROM intimations i
        LEFT JOIN decision_analysis da ON i.id = da.intimation_id
        WHERE i.texto IS NOT NULL
          AND LENGTH(i.texto) > 100  -- Meaningful text only
          AND i.analyzed = TRUE  -- Analyzed documents have better metadata
        ORDER BY RANDOM()
        LIMIT ?
        """

        results = conn.execute(query, [sample_size]).fetchall()
        conn.close()

        for row in results:
            doc = LegalDocument(
                id=row[0],
                texto=row[1],
                decision_type=row[2],
                outcome=row[3],
                nome_classe=row[4],
                tipo_documento=row[5],
                tribunal=row[6],
            )
            self.documents.append(doc)

        console.print(f"  ✓ Loaded {len(self.documents)} documents")
        console.print(f"  • Tribunals: {len(set(d.tribunal for d in self.documents))}")
        console.print(f"  • Document types: {len(set(d.tipo_documento for d in self.documents if d.tipo_documento))}")
        console.print(f"  • Decision types: {len(set(d.decision_type for d in self.documents if d.decision_type))}")

    def generate_test_queries(self) -> None:
        """Generate test queries based on document metadata.

        Creates queries for different search scenarios:
        1. Decision type search (e.g., "sentenças procedentes")
        2. Outcome search (e.g., "recursos providos")
        3. Document class search (e.g., "apelação cível")
        4. Semantic similarity (random document excerpts)
        """
        console.print("\n[cyan]Generating test queries...[/cyan]")

        # Group documents by metadata
        by_decision_type: dict[str, list[LegalDocument]] = {}
        by_outcome: dict[str, list[LegalDocument]] = {}
        by_nome_classe: dict[str, list[LegalDocument]] = {}

        for doc in self.documents:
            if doc.decision_type:
                by_decision_type.setdefault(doc.decision_type, []).append(doc)
            if doc.outcome:
                by_outcome.setdefault(doc.outcome, []).append(doc)
            if doc.nome_classe:
                by_nome_classe.setdefault(doc.nome_classe, []).append(doc)

        # 1. Decision type queries (40% of queries)
        decision_type_queries = [
            ("decisões procedentes em processos cíveis", "procedente", "DECISION_TYPE"),
            ("sentenças de improcedência", "improcedente", "DECISION_TYPE"),
            ("decisões parcialmente procedentes", "parcial", "DECISION_TYPE"),
        ]

        for query_text, keyword, category in decision_type_queries:
            relevant_docs = [
                doc.id
                for doc in self.documents
                if doc.decision_type and keyword.lower() in doc.decision_type.lower()
            ]
            if len(relevant_docs) >= 3:  # Only add if we have enough relevant docs
                self.queries.append(
                    SearchQuery(
                        query_text=query_text,
                        relevant_doc_ids=set(relevant_docs),
                        category=category,
                    )
                )

        # 2. Outcome queries (40% of queries)
        outcome_queries = [
            ("recursos providos pelo tribunal", "provido", "OUTCOME"),
            ("recursos negados ou improvidos", "improvido", "OUTCOME"),
            ("recursos parcialmente providos", "parcial", "OUTCOME"),
        ]

        for query_text, keyword, category in outcome_queries:
            relevant_docs = [
                doc.id for doc in self.documents if doc.outcome and keyword.lower() in doc.outcome.lower()
            ]
            if len(relevant_docs) >= 3:
                self.queries.append(
                    SearchQuery(
                        query_text=query_text,
                        relevant_doc_ids=set(relevant_docs),
                        category=category,
                    )
                )

        # 3. Document class queries (20% of queries)
        # Find most common document classes
        class_counts = {}
        for doc in self.documents:
            if doc.nome_classe:
                class_counts[doc.nome_classe] = class_counts.get(doc.nome_classe, 0) + 1

        top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        for nome_classe, count in top_classes:
            if count >= 3:
                query_text = f"decisões de {nome_classe.lower()}"
                relevant_docs = [doc.id for doc in self.documents if doc.nome_classe == nome_classe]
                self.queries.append(
                    SearchQuery(
                        query_text=query_text,
                        relevant_doc_ids=set(relevant_docs),
                        category="DOCUMENT_CLASS",
                    )
                )

        console.print(f"  ✓ Generated {len(self.queries)} test queries")
        console.print(f"    • Decision type queries: {sum(1 for q in self.queries if q.category == 'DECISION_TYPE')}")
        console.print(f"    • Outcome queries: {sum(1 for q in self.queries if q.category == 'OUTCOME')}")
        console.print(f"    • Document class queries: {sum(1 for q in self.queries if q.category == 'DOCUMENT_CLASS')}")

    async def evaluate_provider(
        self,
        provider_name: str,
        service: EmbeddingService,
    ) -> dict[str, Any]:
        """Evaluate retrieval quality for a provider.

        Args:
            provider_name: Name of the provider.
            service: EmbeddingService instance.

        Returns:
            Evaluation metrics and results.
        """
        console.print(f"\n[cyan]Evaluating {provider_name}...[/cyan]")

        # 1. Embed all documents
        console.print("  • Embedding documents...")
        doc_texts = [doc.texto[:512] for doc in self.documents]  # Limit to max tokens
        doc_embeddings = await service.embed_batch(doc_texts, add_prefix=False)

        # 2. Embed all queries
        console.print("  • Embedding queries...")
        query_texts = [q.query_text for q in self.queries]
        query_embeddings = await service.embed_batch(query_texts, add_prefix=False)

        # 3. Compute retrieval metrics for each query
        all_metrics = []

        for i, query in enumerate(self.queries):
            query_emb = query_embeddings[i]

            # Calculate cosine similarity with all documents
            similarities = []
            for j, doc_emb in enumerate(doc_embeddings):
                similarity = self._cosine_similarity(query_emb, doc_emb)
                similarities.append((self.documents[j].id, similarity))

            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Calculate metrics
            metrics = self._calculate_retrieval_metrics(
                retrieved_ids=[doc_id for doc_id, _ in similarities],
                relevant_ids=query.relevant_doc_ids,
            )
            all_metrics.append(metrics)

        # 4. Aggregate metrics
        avg_metrics = self._aggregate_metrics(all_metrics)

        console.print(f"  ✓ Evaluation complete")
        console.print(f"    • Precision@10: {avg_metrics['precision_at_10']:.3f}")
        console.print(f"    • Recall@10: {avg_metrics['recall_at_10']:.3f}")
        console.print(f"    • NDCG@10: {avg_metrics['ndcg_at_10']:.3f}")
        console.print(f"    • MRR: {avg_metrics['mrr']:.3f}")

        return {
            "provider": provider_name,
            "model": service.model.name,
            "dimension": service.model.dimension,
            "metrics": avg_metrics,
            "per_query_metrics": all_metrics,
        }

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Handles different dimensions by padding with zeros.
        """
        # Pad shorter vector with zeros
        if len(vec1) != len(vec2):
            max_len = max(len(vec1), len(vec2))
            vec1 = vec1 + [0.0] * (max_len - len(vec1))
            vec2 = vec2 + [0.0] * (max_len - len(vec2))

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _calculate_retrieval_metrics(
        self,
        retrieved_ids: list[int],
        relevant_ids: set[int],
    ) -> RetrievalMetrics:
        """Calculate retrieval metrics for a single query.

        Args:
            retrieved_ids: List of document IDs in ranked order.
            relevant_ids: Set of relevant document IDs.

        Returns:
            RetrievalMetrics object.
        """
        # Precision and Recall at K
        def precision_at_k(k: int) -> float:
            if k == 0:
                return 0.0
            top_k = retrieved_ids[:k]
            relevant_retrieved = len([doc_id for doc_id in top_k if doc_id in relevant_ids])
            return relevant_retrieved / k

        def recall_at_k(k: int) -> float:
            if len(relevant_ids) == 0:
                return 0.0
            top_k = retrieved_ids[:k]
            relevant_retrieved = len([doc_id for doc_id in top_k if doc_id in relevant_ids])
            return relevant_retrieved / len(relevant_ids)

        # NDCG (Normalized Discounted Cumulative Gain)
        def ndcg_at_k(k: int) -> float:
            if len(relevant_ids) == 0:
                return 0.0

            # DCG: sum of (relevance / log2(position + 1))
            dcg = 0.0
            for i, doc_id in enumerate(retrieved_ids[:k]):
                if doc_id in relevant_ids:
                    dcg += 1.0 / math.log2(i + 2)  # i+2 because positions start at 1

            # IDCG: DCG of perfect ranking
            idcg = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(relevant_ids))))

            return dcg / idcg if idcg > 0 else 0.0

        # MRR (Mean Reciprocal Rank)
        def calculate_mrr() -> float:
            for i, doc_id in enumerate(retrieved_ids):
                if doc_id in relevant_ids:
                    return 1.0 / (i + 1)
            return 0.0

        return RetrievalMetrics(
            precision_at_5=precision_at_k(5),
            precision_at_10=precision_at_k(10),
            recall_at_5=recall_at_k(5),
            recall_at_10=recall_at_k(10),
            ndcg_at_10=ndcg_at_k(10),
            mrr=calculate_mrr(),
        )

    def _aggregate_metrics(self, metrics_list: list[RetrievalMetrics]) -> dict[str, float]:
        """Aggregate metrics across all queries.

        Args:
            metrics_list: List of RetrievalMetrics objects.

        Returns:
            Dictionary of average metrics.
        """
        if not metrics_list:
            return {}

        return {
            "precision_at_5": sum(m.precision_at_5 for m in metrics_list) / len(metrics_list),
            "precision_at_10": sum(m.precision_at_10 for m in metrics_list) / len(metrics_list),
            "recall_at_5": sum(m.recall_at_5 for m in metrics_list) / len(metrics_list),
            "recall_at_10": sum(m.recall_at_10 for m in metrics_list) / len(metrics_list),
            "ndcg_at_10": sum(m.ndcg_at_10 for m in metrics_list) / len(metrics_list),
            "mrr": sum(m.mrr for m in metrics_list) / len(metrics_list),
        }


def print_comparison_table(results: list[dict[str, Any]]) -> None:
    """Print formatted comparison table.

    Args:
        results: List of evaluation results from evaluate_provider().
    """
    table = Table(title="Embedding Quality Comparison (Retrieval Metrics)", show_header=True, header_style="bold magenta")

    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="white")
    table.add_column("Dim", justify="right", style="green")
    table.add_column("P@10", justify="right", style="yellow")
    table.add_column("R@10", justify="right", style="blue")
    table.add_column("NDCG@10", justify="right", style="magenta")
    table.add_column("MRR", justify="right", style="cyan")

    for result in results:
        metrics = result["metrics"]
        table.add_row(
            result["provider"].upper(),
            result["model"][:30],  # Truncate long model names
            str(result["dimension"]),
            f"{metrics['precision_at_10']:.3f}",
            f"{metrics['recall_at_10']:.3f}",
            f"{metrics['ndcg_at_10']:.3f}",
            f"{metrics['mrr']:.3f}",
        )

    console.print("\n")
    console.print(table)
    console.print("\n")


def print_analysis(results: list[dict[str, Any]]) -> None:
    """Print quality analysis and recommendations.

    Args:
        results: List of evaluation results.
    """
    console.print("[bold green]Quality Analysis:[/bold green]\n")

    # Find best provider for each metric
    best_precision = max(results, key=lambda r: r["metrics"]["precision_at_10"])
    best_recall = max(results, key=lambda r: r["metrics"]["recall_at_10"])
    best_ndcg = max(results, key=lambda r: r["metrics"]["ndcg_at_10"])
    best_mrr = max(results, key=lambda r: r["metrics"]["mrr"])

    console.print(f"🎯 Best Precision@10: [bold]{best_precision['provider'].upper()}[/bold] ({best_precision['metrics']['precision_at_10']:.3f})")
    console.print(f"📊 Best Recall@10: [bold]{best_recall['provider'].upper()}[/bold] ({best_recall['metrics']['recall_at_10']:.3f})")
    console.print(f"⭐ Best NDCG@10: [bold]{best_ndcg['provider'].upper()}[/bold] ({best_ndcg['metrics']['ndcg_at_10']:.3f})")
    console.print(f"🥇 Best MRR: [bold]{best_mrr['provider'].upper()}[/bold] ({best_mrr['metrics']['mrr']:.3f})")

    # Quality thresholds
    console.print("\n[bold cyan]Quality Interpretation:[/bold cyan]")
    console.print("  • Precision@10 > 0.7: Excellent relevance")
    console.print("  • Precision@10 > 0.5: Good relevance")
    console.print("  • Precision@10 < 0.3: Poor relevance (not recommended)")
    console.print("\n  • Recall@10 > 0.7: Excellent coverage")
    console.print("  • Recall@10 > 0.5: Good coverage")
    console.print("\n  • NDCG@10 > 0.7: Excellent ranking quality")
    console.print("  • NDCG@10 > 0.5: Good ranking quality")

    # Recommendations
    console.print("\n[bold green]Recommendations:[/bold green]")
    for result in results:
        provider = result["provider"].upper()
        metrics = result["metrics"]
        precision = metrics["precision_at_10"]
        ndcg = metrics["ndcg_at_10"]

        if precision >= 0.7 and ndcg >= 0.7:
            console.print(f"  ✅ {provider}: Excellent quality - Recommended for production")
        elif precision >= 0.5 and ndcg >= 0.5:
            console.print(f"  ⚠️  {provider}: Good quality - Acceptable for production")
        else:
            console.print(f"  ❌ {provider}: Quality concerns - Not recommended")


@app.command()
def main(
    providers: list[str] = typer.Option(
        ["local", "jina"],
        "--providers",
        "-p",
        help="Providers to benchmark",
    ),
    sample_size: int = typer.Option(
        200,
        "--sample-size",
        "-n",
        help="Number of documents to sample",
    ),
    db_path: str = typer.Option(
        str(settings.DB_PATH),
        "--db",
        help="Path to DuckDB database",
    ),
) -> None:
    """Run embedding quality benchmark on real legal documents.

    Tests retrieval accuracy using actual CausaGanha legal data.
    """
    console.print("[bold]Embedding Quality Benchmark (Real Legal Data)[/bold]")
    console.print(f"Database: {db_path}")
    console.print(f"Providers: {', '.join(providers)}")
    console.print(f"Sample size: {sample_size} documents\n")

    try:
        # Initialize benchmark
        benchmark = EmbeddingQualityBenchmark(db_path)

        # Load data
        benchmark.load_documents(sample_size)
        benchmark.generate_test_queries()

        if not benchmark.queries:
            console.print("[red]Error: No test queries generated. Not enough documents with metadata.[/red]")
            raise typer.Exit(1)

        # Evaluate each provider
        results = []

        async def run_evaluations():
            for provider in providers:
                try:
                    console.print(f"\n[cyan]Initializing {provider} provider...[/cyan]")
                    service = await EmbeddingService.create(provider=provider)
                    result = await benchmark.evaluate_provider(provider, service)
                    results.append(result)
                except Exception as e:
                    console.print(f"[red]Failed to evaluate {provider}: {e}[/red]")
                    logger.exception("provider_evaluation_failed", provider=provider)

        asyncio.run(run_evaluations())

        if results:
            print_comparison_table(results)
            print_analysis(results)

            # Export results
            import json

            output_file = Path("data/quality_benchmark_results.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("w") as f:
                json.dump(results, f, indent=2, default=str)

            console.print(f"\n[green]Results exported to: {output_file}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Benchmark failed: {e}[/red]")
        logger.exception("benchmark_failed", error=str(e))
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
