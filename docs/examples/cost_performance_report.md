# Cost & Performance Report (Sprint 2025-03)

This document summarizes quick benchmarks and cost estimates produced during the sprint.

## DuckDB Join Benchmark
- Benchmark implemented in `tests/benchmarks/test_duckdb_join_benchmark.py`.
- Joining two 100k-row tables completed in under one second on a standard laptop.

## Storage Cost Estimate
- `storage_cost_analysis.py` calculates Internet Archive storage costs at **$6 per TB-month**.
- Current database (~1 GiB) would cost roughly **$0.006 per month**.

## Pipeline Profiling
- `pipeline_profiling_example.py` runs the async pipeline with `--stats-only` and prints runtime and peak memory usage using `tracemalloc`.
- On a local test with one item, runtime was under a second with peak memory usage below 50&nbsp;MB.
