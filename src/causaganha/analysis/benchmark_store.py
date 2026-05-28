"""Benchmark dataset store — records every LLM-classified decision.

Every text that reaches the LLM is a candidate for the benchmark:
it was ambiguous enough that keyword + RAG couldn't handle it alone,
making it a valuable hard example. Over time the dataset grows and
can be used to:

  - Measure accuracy of keyword / RAG vs ground truth (LLM labels)
  - Train or retrain the anchor classifier
  - Drive the pattern suggestion loop (LLM proposes new heuristics)

Storage:
  - Append to ``data/benchmark/pending.jsonl`` (one JSON object per line)
  - Periodically compacted to ``data/benchmark/benchmark.parquet``
    by running ``scripts/compact_benchmark.py``

Record schema:
  text_snippet      str   First 1000 chars of the plain-text decision
  outcome           str   LLM-determined outcome (canonical key)
  confidence        float LLM confidence score
  keyword_conf      float KeywordClassifier confidence (0.0 if no match)
  model             str   LiteLLM model identifier used
  timestamp         str   ISO-8601 UTC
  intimation_id     int   Source intimation ID (0 if unknown)
  analysis_method   str   "llm" | "hybrid"
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import structlog


logger = structlog.get_logger()

DEFAULT_BENCHMARK_DIR = Path("data/benchmark")
_PENDING_FILE = "pending.jsonl"


class BenchmarkStore:
    """Thread-safe append-only store for LLM-classified decisions.

    Records are flushed immediately to disk (one JSON line per call).
    Thread-safe via a reentrant lock — safe for async workloads that
    call flush from a thread-pool executor.
    """

    def __init__(self, benchmark_dir: Path | str = DEFAULT_BENCHMARK_DIR) -> None:
        """Initialize store with path to benchmark directory."""
        self.benchmark_dir = Path(benchmark_dir)
        self._pending_path = self.benchmark_dir / _PENDING_FILE
        self._lock = threading.Lock()

    def record(
        self,
        *,
        text: str,
        outcome: str,
        confidence: float,
        model: str,
        keyword_conf: float = 0.0,
        intimation_id: int = 0,
        analysis_method: str = "llm",
    ) -> None:
        """Append one benchmark record to the pending JSONL file.

        Args:
            text: Plain-text decision (HTML already stripped).
            outcome: LLM-determined outcome string.
            confidence: LLM confidence score.
            model: LiteLLM model identifier.
            keyword_conf: KeywordClassifier confidence (0.0 = no match).
            intimation_id: Source intimation ID.
            analysis_method: "llm" or "hybrid".
        """
        row = {
            "text_snippet": text[:1000],
            "outcome": outcome,
            "confidence": confidence,
            "keyword_conf": keyword_conf,
            "model": model,
            "timestamp": datetime.now(UTC).isoformat(),
            "intimation_id": intimation_id,
            "analysis_method": analysis_method,
        }
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        with self._lock, self._pending_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

        logger.debug(
            "benchmark_record_written",
            outcome=outcome,
            model=model,
            intimation_id=intimation_id,
        )

    def pending_count(self) -> int:
        """Return number of uncompacted records in pending.jsonl."""
        if not self._pending_path.exists():
            return 0
        with self._lock:
            return sum(1 for _ in self._pending_path.open(encoding="utf-8"))

    def compact(self) -> int:
        """Compact pending.jsonl into benchmark.parquet.

        Returns number of records written. Safe to call from a
        maintenance script; during normal operation records stay in JSONL.
        """
        import ibis  # noqa: PLC0415

        if not self._pending_path.exists():
            return 0

        with self._lock:
            text = self._pending_path.read_text(encoding="utf-8")
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]

        if not rows:
            return 0

        parquet_path = self.benchmark_dir / "benchmark.parquet"
        new_table = ibis.memtable(rows)

        if parquet_path.exists():
            existing = ibis.read_parquet(parquet_path)
            combined = existing.union(new_table)
        else:
            combined = new_table

        combined_df = combined.execute()
        ibis.memtable(combined_df).to_parquet(str(parquet_path))

        with self._lock:
            self._pending_path.unlink()

        n = len(combined_df)
        logger.info("benchmark_compacted", total_records=n, path=str(parquet_path))
        return n
