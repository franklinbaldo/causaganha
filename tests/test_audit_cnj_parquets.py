"""Tests for scripts/audit_cnj_parquets.py — issue #1470 classification logic."""

from __future__ import annotations

import duckdb
import httpx

from scripts.audit_cnj_parquets import (
    CONFORMANT,
    NOT_APPLICABLE,
    REORDER_CANDIDATE,
    UNAVAILABLE,
    VERIFY_VALUES,
    classify_file,
    is_tribunal_year_item,
    list_djen_items,
    ranges_overlap,
    read_footer_stats,
)


class TestRangesOverlap:
    def test_disjoint_ascending_ranges_do_not_overlap(self) -> None:
        assert ranges_overlap([("001", "010"), ("011", "020"), ("021", "030")]) is False

    def test_ranges_sharing_a_group_boundary_overlap(self) -> None:
        assert ranges_overlap([("001", "010"), ("010", "020")]) is True

    def test_interleaved_ranges_overlap(self) -> None:
        # Unsorted-by-CNJ data: each row group spans the whole key space.
        assert ranges_overlap([("001", "090"), ("005", "099"), ("002", "050")]) is True

    def test_single_range_never_overlaps(self) -> None:
        assert ranges_overlap([("001", "999")]) is False


class TestClassifyFile:
    def test_conformant_marker_wins_regardless_of_ranges(self) -> None:
        # Even overlapping ranges are irrelevant once the file certifies the
        # normalization/layout contract via KV metadata (issue #1470's
        # "conforme" bucket is decided by the marker, not by re-deriving it
        # from footer stats).
        result = classify_file(
            table_name="comunicacoes",
            has_conformant_marker=True,
            row_group_ranges=[("050", "010"), ("001", "099")],
            read_error=None,
        )
        assert result == CONFORMANT

    def test_overlapping_ranges_across_groups_is_reorder_candidate(self) -> None:
        result = classify_file(
            table_name="comunicacoes",
            has_conformant_marker=False,
            row_group_ranges=[("001", "090"), ("005", "099")],
            read_error=None,
        )
        assert result == REORDER_CANDIDATE

    def test_single_row_group_is_verify_values_not_conformant(self) -> None:
        # A lone row group can look "sorted" by definition of having only one
        # min/max pair, but the issue explicitly warns that footer stats alone
        # never prove internal ordering -- only content verification does.
        result = classify_file(
            table_name="comunicacoes",
            has_conformant_marker=False,
            row_group_ranges=[("001", "999")],
            read_error=None,
        )
        assert result == VERIFY_VALUES

    def test_non_overlapping_ranges_without_marker_is_still_verify_values(self) -> None:
        # Issue #1470 acceptance criteria: "ausencia de sobreposicao entre
        # grupos nao prova normalizacao ou ordenacao interna" -- non-overlap
        # is necessary but not sufficient evidence of a sorted, certified file.
        result = classify_file(
            table_name="comunicacoes",
            has_conformant_marker=False,
            row_group_ranges=[("001", "010"), ("011", "020")],
            read_error=None,
        )
        assert result == VERIFY_VALUES

    def test_table_without_a_cnj_column_is_not_applicable(self) -> None:
        result = classify_file(
            table_name="destinatarios",
            has_conformant_marker=False,
            row_group_ranges=[],
            read_error=None,
        )
        assert result == NOT_APPLICABLE

    def test_read_error_is_unavailable_not_absent(self) -> None:
        # Mirrors CLAUDE.md's DJEN 403-vs-absent rule: a fetch/read failure is
        # an unknown gap, never evidence the file needs (or doesn't need)
        # reordering.
        result = classify_file(
            table_name="comunicacoes",
            has_conformant_marker=False,
            row_group_ranges=[],
            read_error="HTTP 403",
        )
        assert result == UNAVAILABLE

    def test_read_error_overrides_not_applicable_table(self) -> None:
        result = classify_file(
            table_name="destinatarios",
            has_conformant_marker=False,
            row_group_ranges=[],
            read_error="timeout",
        )
        assert result == UNAVAILABLE

    def test_a_range_with_a_null_bound_forces_verify_values(self) -> None:
        # An all-null-CNJ row group has no derivable min/max; we cannot prove
        # or disprove overlap against it, so don't guess either way.
        result = classify_file(
            table_name="comunicacoes",
            has_conformant_marker=False,
            row_group_ranges=[("001", "010"), (None, None)],
            read_error=None,
        )
        assert result == VERIFY_VALUES


class TestIsTribunalYearItem:
    def test_accepts_current_tribunal_year_naming(self) -> None:
        assert is_tribunal_year_item("djen-tjro-2025") is True

    def test_accepts_hyphenated_tribunal_codes(self) -> None:
        assert is_tribunal_year_item("djen-tre-ac-2025") is True

    def test_rejects_discontinued_per_day_naming(self) -> None:
        assert is_tribunal_year_item("djen-2026-01-15") is False

    def test_rejects_unrelated_identifier(self) -> None:
        assert is_tribunal_year_item("causaganha-catalog") is False


class TestListDjenItems:
    def test_filters_out_legacy_per_day_items(self) -> None:
        payload = {
            "response": {
                "docs": [
                    {"identifier": "djen-tjro-2025"},
                    {"identifier": "djen-2026-01-15"},
                    {"identifier": "djen-tre-ac-2024"},
                ]
            }
        }
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        with httpx.Client(transport=transport) as client:
            items = list_djen_items(client)

        assert items == sorted(["djen-tjro-2025", "djen-tre-ac-2024"])
        assert "djen-2026-01-15" not in items


class TestReadFooterStats:
    def test_round_trips_through_a_real_unsorted_parquet_fixture(self, tmp_path) -> None:
        path = tmp_path / "comunicacoes.parquet"
        con = duckdb.connect(":memory:")
        con.execute(
            "CREATE TABLE t AS "
            "SELECT lpad(((i * 37) % 1000)::VARCHAR, 3, '0') AS numero_processo "
            "FROM range(1, 3001) t(i)"
        )
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET, ROW_GROUP_SIZE 500)")

        stats = read_footer_stats(str(path), table_name="comunicacoes")

        assert stats.read_error is None
        assert stats.row_count == 3000
        assert len(stats.row_group_ranges) >= 2
        assert stats.kv_metadata == {}
        assert (
            classify_file(
                table_name="comunicacoes",
                has_conformant_marker=False,
                row_group_ranges=stats.row_group_ranges,
                read_error=stats.read_error,
            )
            == REORDER_CANDIDATE
        )

    def test_round_trips_through_a_real_certified_parquet_fixture(self, tmp_path) -> None:
        path = tmp_path / "comunicacoes.parquet"
        con = duckdb.connect(":memory:")
        con.execute(
            "CREATE TABLE t AS "
            "SELECT lpad(i::VARCHAR, 3, '0') AS numero_processo FROM range(1, 3001) t(i)"
        )
        con.execute(
            f"COPY (SELECT * FROM t ORDER BY numero_processo) TO '{path}' "
            "(FORMAT PARQUET, ROW_GROUP_SIZE 500, "
            "KV_METADATA {'causaganha.layout': 'cnj-text-sorted-v1'})"
        )

        stats = read_footer_stats(str(path), table_name="comunicacoes")

        assert stats.read_error is None
        assert stats.kv_metadata.get("causaganha.layout") == "cnj-text-sorted-v1"

    def test_missing_file_is_unavailable_not_a_crash(self, tmp_path) -> None:
        stats = read_footer_stats(
            str(tmp_path / "does-not-exist.parquet"), table_name="comunicacoes"
        )

        assert stats.read_error is not None
        assert stats.row_count == 0
        assert stats.row_group_ranges == []

    def test_table_without_cnj_column_skips_range_extraction(self, tmp_path) -> None:
        path = tmp_path / "destinatarios.parquet"
        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE t AS SELECT i AS comunicacao_id FROM range(1, 101) t(i)")
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET)")

        stats = read_footer_stats(str(path), table_name="destinatarios")

        assert stats.read_error is None
        assert stats.row_group_ranges == []
        assert (
            classify_file(
                table_name="destinatarios",
                has_conformant_marker=False,
                row_group_ranges=stats.row_group_ranges,
                read_error=stats.read_error,
            )
            == NOT_APPLICABLE
        )
