"""Tests for the covering-index decision used by issue #1469's A1c gate.

`decide_covering_index` is the network-free, injectable piece of
`scripts/benchmarks/bloom_filter_production.py`: it turns per-ordering
`OrderingMeasurement`s (min/max pruning results against a real rewritten
Parquet file) into a decision on whether an additive covering index (plan
§1c, step 2) is needed. `run`, which downloads/rewrites a real production
file via DuckDB, is not covered here, matching this repo's existing
convention for `row_group_size_production.py` and `archive_cors_probe.py`.
"""

from __future__ import annotations

from scripts.benchmarks.bloom_filter_production import (
    OrderingMeasurement,
    decide_covering_index,
)


def _measurement(
    ordering: str, *, touched_for_cnj_lookup: int, bloom_row_groups: int = 0
) -> OrderingMeasurement:
    return OrderingMeasurement(
        ordering=ordering,
        order_by="irrelevant for this decision",
        row_group_count=9,
        row_groups_with_bloom_filter=bloom_row_groups,
        distinct_encodings=["PLAIN"],
        row_groups_touched_for_cnj_lookup_minmax=touched_for_cnj_lookup,
        per_row_group=[],
    )


class TestDecideCoveringIndex:
    def test_cnj_first_pruning_to_one_row_group_makes_index_unnecessary(self) -> None:
        """Real A1b evidence: CNJ point-lookup already touches 1 row group via min/max
        alone on the cnj_first (production) ordering -- no bloom filter needed."""
        measurements = [
            _measurement("cnj_first", touched_for_cnj_lookup=1),
            _measurement("date_first", touched_for_cnj_lookup=9),
        ]

        needed, rationale = decide_covering_index(measurements)

        assert needed is False
        assert "min/max" in rationale

    def test_cnj_first_not_pruning_to_one_group_flags_index_as_needed(self) -> None:
        """If min/max alone can't isolate the CNJ to a single row group even on the
        cnj_first ordering, a covering index (or bloom filter) is a real gap."""
        measurements = [
            _measurement("cnj_first", touched_for_cnj_lookup=3),
            _measurement("date_first", touched_for_cnj_lookup=9),
        ]

        needed, rationale = decide_covering_index(measurements)

        assert needed is True
        assert "não reduziu" in rationale

    def test_decision_only_looks_at_the_cnj_first_ordering(self) -> None:
        """The production layout is cnj_first (exporter.py) -- date_first is only
        measured for contrast with the synthetic benchmark, not for the decision."""
        measurements = [
            _measurement("date_first", touched_for_cnj_lookup=1),
            _measurement("cnj_first", touched_for_cnj_lookup=1),
        ]

        needed, _rationale = decide_covering_index(measurements)

        assert needed is False
