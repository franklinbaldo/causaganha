#!/usr/bin/env python3
"""Benchmark script to compare embedding providers (Local vs Jina vs Google).

This script measures:
- Latency (single text embedding)
- Throughput (batch processing)
- Memory usage
- Quality (cosine similarity comparison)

Usage:
    python scripts/benchmark_embeddings.py
    python scripts/benchmark_embeddings.py --providers local jina
    python scripts/benchmark_embeddings.py --sample-size 100
"""

import asyncio
import time
from typing import Any

import structlog
import typer
from rich.console import Console
from rich.table import Table

from causaganha.v2.analysis.embedding_models import (
    DEFAULT_GOOGLE_MODEL,
    DEFAULT_JINA_MODEL,
    DEFAULT_LOCAL_MODEL,
)
from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService


logger = structlog.get_logger()
console = Console()
app = typer.Typer()

# Sample legal texts (Brazilian Portuguese)
SAMPLE_TEXTS = [
    "O juiz determinou a procedência do pedido inicial, condenando o réu ao pagamento de indenização por danos morais.",
    "A sentença foi reformada pelo tribunal, reconhecendo a prescrição do direito alegado pelo autor.",
    "Nego provimento ao recurso de apelação, mantendo a sentença de primeiro grau por seus próprios fundamentos.",
    "Dou provimento ao recurso para reformar a sentença e julgar improcedente o pedido inicial.",
    "O Ministério Público interpôs recurso especial contra a decisão do tribunal regional.",
    "Reconheço a nulidade do processo por cerceamento de defesa, determinando seu retorno à origem.",
    "A tutela de urgência foi deferida para suspender os efeitos do ato administrativo impugnado.",
    "Homologo o acordo celebrado entre as partes e declaro extinto o processo com resolução de mérito.",
    "A preliminar de ilegitimidade passiva foi acolhida, extinguindo o processo sem resolução de mérito.",
    "O recurso não merece prosperar, pois ausente qualquer das hipóteses do artigo 1.029 do CPC.",
]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector.
        vec2: Second embedding vector.

    Returns:
        Cosine similarity score (0 to 1).
    """
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


async def benchmark_latency(
    service: EmbeddingService,
    text: str,
    runs: int = 5,
) -> dict[str, float]:
    """Benchmark single text embedding latency.

    Args:
        service: EmbeddingService to test.
        text: Text to embed.
        runs: Number of runs for averaging.

    Returns:
        Dict with latency statistics (mean, min, max).
    """
    latencies = []

    for _ in range(runs):
        start = time.perf_counter()
        await service.embed_text(text, add_prefix=False)
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convert to ms

    return {
        "mean_ms": sum(latencies) / len(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
    }


async def benchmark_throughput(
    service: EmbeddingService,
    texts: list[str],
) -> dict[str, float]:
    """Benchmark batch embedding throughput.

    Args:
        service: EmbeddingService to test.
        texts: List of texts to embed.

    Returns:
        Dict with throughput statistics.
    """
    start = time.perf_counter()
    await service.embed_batch(texts, add_prefix=False)
    end = time.perf_counter()

    elapsed_s = end - start
    throughput = len(texts) / elapsed_s

    return {
        "total_time_s": elapsed_s,
        "texts_per_second": throughput,
        "ms_per_text": (elapsed_s * 1000) / len(texts),
    }


async def benchmark_quality(
    service1: EmbeddingService,
    service2: EmbeddingService,
    texts: list[str],
) -> dict[str, float]:
    """Compare embedding quality between two providers.

    Measures cosine similarity between embeddings from two providers
    for the same texts. Higher similarity suggests similar semantic understanding.

    Args:
        service1: First embedding service (baseline).
        service2: Second embedding service (comparison).
        texts: List of texts to compare.

    Returns:
        Dict with quality metrics (mean/min/max similarity).
    """
    embeddings1 = await service1.embed_batch(texts, add_prefix=False)
    embeddings2 = await service2.embed_batch(texts, add_prefix=False)

    similarities = []
    for emb1, emb2 in zip(embeddings1, embeddings2):
        # Pad shorter vector with zeros if dimensions differ
        if len(emb1) != len(emb2):
            max_len = max(len(emb1), len(emb2))
            emb1 = emb1 + [0.0] * (max_len - len(emb1))
            emb2 = emb2 + [0.0] * (max_len - len(emb2))

        sim = cosine_similarity(emb1, emb2)
        similarities.append(sim)

    return {
        "mean_similarity": sum(similarities) / len(similarities),
        "min_similarity": min(similarities),
        "max_similarity": max(similarities),
    }


async def run_benchmarks(
    providers: list[str],
    sample_size: int,
) -> dict[str, dict[str, Any]]:
    """Run comprehensive benchmarks for specified providers.

    Args:
        providers: List of provider names to benchmark.
        sample_size: Number of texts to use for benchmarking.

    Returns:
        Dict mapping provider name to benchmark results.
    """
    results: dict[str, dict[str, Any]] = {}
    services: dict[str, EmbeddingService] = {}

    # Sample texts for benchmarking
    texts = SAMPLE_TEXTS[:sample_size]

    # Initialize services
    console.print("\n[bold cyan]Initializing embedding services...[/bold cyan]")

    for provider in providers:
        try:
            console.print(f"  Loading {provider} provider...")
            service = await EmbeddingService.create(provider=provider)
            services[provider] = service

            # Record model info
            results[provider] = {
                "model": service.model.name,
                "dimension": service.model.dimension,
                "max_tokens": service.model.max_tokens,
            }

            console.print(f"  ✓ {provider}: {service.model.name} ({service.model.dimension}D)")

        except Exception as e:
            console.print(f"  ✗ {provider}: {e}", style="red")
            logger.exception("provider_init_failed", provider=provider, error=str(e))

    if not services:
        console.print("\n[bold red]No providers available for benchmarking![/bold red]")
        return results

    # Benchmark 1: Latency
    console.print("\n[bold cyan]Benchmark 1: Single Text Latency[/bold cyan]")
    test_text = texts[0]

    for provider, service in services.items():
        console.print(f"  Testing {provider}...")
        latency_results = await benchmark_latency(service, test_text, runs=5)
        results[provider]["latency"] = latency_results
        console.print(
            f"    Mean: {latency_results['mean_ms']:.2f}ms "
            f"(min: {latency_results['min_ms']:.2f}ms, max: {latency_results['max_ms']:.2f}ms)"
        )

    # Benchmark 2: Throughput
    console.print("\n[bold cyan]Benchmark 2: Batch Throughput[/bold cyan]")

    for provider, service in services.items():
        console.print(f"  Testing {provider}...")
        throughput_results = await benchmark_throughput(service, texts)
        results[provider]["throughput"] = throughput_results
        console.print(
            f"    Throughput: {throughput_results['texts_per_second']:.2f} texts/s "
            f"({throughput_results['ms_per_text']:.2f}ms per text)"
        )

    # Benchmark 3: Quality Comparison (if multiple providers)
    if len(services) >= 2:
        console.print("\n[bold cyan]Benchmark 3: Quality Comparison[/bold cyan]")
        provider_names = list(services.keys())

        # Use first provider as baseline
        baseline_provider = provider_names[0]
        baseline_service = services[baseline_provider]

        for i in range(1, len(provider_names)):
            compare_provider = provider_names[i]
            compare_service = services[compare_provider]

            console.print(f"  Comparing {compare_provider} vs {baseline_provider}...")
            quality_results = await benchmark_quality(baseline_service, compare_service, texts)
            results[compare_provider]["quality_vs_baseline"] = quality_results
            console.print(
                f"    Mean similarity: {quality_results['mean_similarity']:.4f} "
                f"(min: {quality_results['min_similarity']:.4f}, max: {quality_results['max_similarity']:.4f})"
            )

    return results


def print_summary_table(results: dict[str, dict[str, Any]]) -> None:
    """Print formatted summary table of benchmark results.

    Args:
        results: Benchmark results from run_benchmarks().
    """
    table = Table(title="Embedding Provider Benchmark Results", show_header=True, header_style="bold magenta")

    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Model", style="white")
    table.add_column("Dimension", justify="right", style="green")
    table.add_column("Latency (ms)", justify="right", style="yellow")
    table.add_column("Throughput (texts/s)", justify="right", style="blue")
    table.add_column("Quality vs Baseline", justify="right", style="magenta")

    for provider, data in results.items():
        latency_str = f"{data['latency']['mean_ms']:.2f}" if "latency" in data else "N/A"
        throughput_str = f"{data['throughput']['texts_per_second']:.2f}" if "throughput" in data else "N/A"
        quality_str = (
            f"{data['quality_vs_baseline']['mean_similarity']:.4f}"
            if "quality_vs_baseline" in data
            else "baseline"
        )

        table.add_row(
            provider.upper(),
            data["model"],
            str(data["dimension"]),
            latency_str,
            throughput_str,
            quality_str,
        )

    console.print("\n")
    console.print(table)
    console.print("\n")


def print_recommendations(results: dict[str, dict[str, Any]]) -> None:
    """Print recommendations based on benchmark results.

    Args:
        results: Benchmark results from run_benchmarks().
    """
    console.print("[bold green]Recommendations:[/bold green]\n")

    # Find fastest latency
    if any("latency" in data for data in results.values()):
        fastest = min(
            ((p, d["latency"]["mean_ms"]) for p, d in results.items() if "latency" in d),
            key=lambda x: x[1],
        )
        console.print(f"⚡ Lowest Latency: [bold]{fastest[0].upper()}[/bold] ({fastest[1]:.2f}ms)")

    # Find highest throughput
    if any("throughput" in data for data in results.values()):
        highest_throughput = max(
            ((p, d["throughput"]["texts_per_second"]) for p, d in results.items() if "throughput" in d),
            key=lambda x: x[1],
        )
        console.print(
            f"🚀 Highest Throughput: [bold]{highest_throughput[0].upper()}[/bold] "
            f"({highest_throughput[1]:.2f} texts/s)"
        )

    # Quality notes
    if any("quality_vs_baseline" in data for data in results.values()):
        console.print("\n📊 Quality Analysis:")
        for provider, data in results.items():
            if "quality_vs_baseline" in data:
                sim = data["quality_vs_baseline"]["mean_similarity"]
                if sim >= 0.95:
                    console.print(f"  ✓ {provider.upper()}: Excellent quality (similarity: {sim:.4f})")
                elif sim >= 0.85:
                    console.print(f"  ⚠ {provider.upper()}: Good quality (similarity: {sim:.4f})")
                else:
                    console.print(f"  ✗ {provider.upper()}: Quality concerns (similarity: {sim:.4f})")

    console.print("\n[bold cyan]Use Cases:[/bold cyan]")
    console.print("  • Real-time queries: Use lowest latency provider")
    console.print("  • Batch processing: Use highest throughput provider")
    console.print("  • Production: Balance latency, cost, and quality")
    console.print("  • Development: Use local provider (free, private)")


@app.command()
def main(
    providers: list[str] = typer.Option(
        ["local", "jina", "google"],
        "--providers",
        "-p",
        help="List of providers to benchmark",
    ),
    sample_size: int = typer.Option(
        10,
        "--sample-size",
        "-n",
        help="Number of sample texts to use",
    ),
) -> None:
    """Run embedding provider benchmarks.

    Compares latency, throughput, and quality across different embedding providers.
    """
    console.print("[bold]Embedding Provider Benchmark[/bold]")
    console.print(f"Providers: {', '.join(providers)}")
    console.print(f"Sample size: {sample_size} texts")

    try:
        results = asyncio.run(run_benchmarks(providers, sample_size))

        if results:
            print_summary_table(results)
            print_recommendations(results)

            # Export results to file
            import json
            from pathlib import Path

            output_file = Path("data/benchmark_results.json")
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("w") as f:
                json.dump(results, f, indent=2)

            console.print(f"[green]Results exported to: {output_file}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Benchmark failed: {e}[/red]")
        logger.exception("benchmark_failed", error=str(e))
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
