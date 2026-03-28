MAGIC_VAL_2 = 2
MAGIC_VAL_95 = 95
MAGIC_VAL_10 = 10

"""Experiment: Stress test Jina AI embeddings to find optimal rate limits.

This script tests Jina embedding API with increasing concurrency to determine:
1. Maximum concurrent requests before rate limiting
2. Optimal concurrency for production use
3. Rate limit recovery time
4. Error patterns and retry strategies
"""

import asyncio
import time
from typing import Any

import structlog

from causaganha.analysis.embedding_service import EmbeddingService


# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger()

# Sample Brazilian legal text for testing
SAMPLE_TEXT = """
ACÓRDÃO: Vistos, relatados e discutidos estes autos, acordam os Desembargadores
da 1ª Câmara Cível do Tribunal de Justiça, por unanimidade, em conhecer do
recurso e dar-lhe provimento para reformar a sentença de primeiro grau.
"""


async def test_concurrent_embeddings(
    concurrency: int,
    total_requests: int,
    service: EmbeddingService,
) -> dict[str, Any]:
    """Test embedding generation with specific concurrency level.

    Args:
        concurrency: Number of concurrent requests
        total_requests: Total number of requests to make
        service: EmbeddingService instance

    Returns:
        Dictionary with test results
    """
    start_time = time.time()
    successes = 0
    rate_limited = 0
    errors = 0
    latencies = []

    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)

    async def make_request(request_num: int) -> None:
        nonlocal successes, rate_limited, errors
        async with semaphore:
            req_start = time.time()
            try:
                await service.embed_text(
                    f"{SAMPLE_TEXT} Request {request_num}",
                    add_prefix=False,
                )
                req_time = time.time() - req_start
                latencies.append(req_time)
                successes += 1
            except Exception as e:
                req_time = time.time() - req_start
                error_str = str(e).lower()
                if "429" in error_str or "too many" in error_str:
                    rate_limited += 1
                else:
                    errors += 1
                    logger.debug(
                        "request_error",
                        request_num=request_num,
                        error=str(e),
                        latency=req_time,
                    )

    # Execute all requests
    tasks = [make_request(i) for i in range(total_requests)]
    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time

    # Calculate statistics
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p50_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successes": successes,
        "rate_limited": rate_limited,
        "errors": errors,
        "elapsed_time": elapsed,
        "requests_per_second": total_requests / elapsed if elapsed > 0 else 0,
        "avg_latency": avg_latency,
        "p50_latency": p50_latency,
        "p95_latency": p95_latency,
        "p99_latency": p99_latency,
        "success_rate": (successes / total_requests * 100) if total_requests > 0 else 0,
    }


async def find_optimal_rate() -> None:
    """Find optimal rate limit through progressive stress testing."""
    # Initialize Jina service
    service = EmbeddingService(provider="jina")

    # Test configurations: (concurrency, total_requests)
    test_configs = [
        (1, 10, "Baseline"),
        (5, 20, "Low concurrency"),
        (10, 30, "Medium concurrency"),
        (20, 40, "High concurrency"),
        (50, 50, "Very high concurrency"),
        (100, 100, "Extreme concurrency"),
    ]

    results = []

    for concurrency, total_requests, _description in test_configs:
        result = await test_concurrent_embeddings(concurrency, total_requests, service)

        results.append(result)

        # Display results

        # If we hit significant rate limiting, stop
        if result["rate_limited"] > total_requests * 0.3:  # >30% rate limited
            break

        # Wait between tests to avoid cumulative rate limiting
        if concurrency >= MAGIC_VAL_10:
            wait_time = 5
            await asyncio.sleep(wait_time)

    # Analysis

    # Find optimal concurrency (highest success rate with minimal rate limiting)
    optimal = None
    for result in results:
        if result["success_rate"] >= MAGIC_VAL_95 and result["rate_limited"] <= MAGIC_VAL_2:
            if optimal is None or result["requests_per_second"] > optimal["requests_per_second"]:
                optimal = result

    if optimal:
        # Production recommendations
        safety_margin = 0.7  # Use 70% of optimal to be safe
        max(1, int(optimal["concurrency"] * safety_margin))
        optimal["requests_per_second"] * safety_margin

        # Configuration code

    else:
        pass

    # Summary table
    for result in results:
        pass

    # Rate limiting patterns
    total_rate_limited = sum(r["rate_limited"] for r in results)
    if total_rate_limited > 0:
        breaking_point = next(
            (r for r in results if r["rate_limited"] > r["total_requests"] * 0.2),
            None,
        )
        if breaking_point:
            pass

    # Official documentation comparison


if __name__ == "__main__":
    asyncio.run(find_optimal_rate())
