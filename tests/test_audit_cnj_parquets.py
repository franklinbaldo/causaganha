"""Tests for scripts/audit_cnj_parquets.py — issue #1470 classification logic."""

from __future__ import annotations

import duckdb
import httpx

from scripts.audit_cnj_parquets import (
    CONFORMANT,
    NATIONAL_INDEX,
    NATIONAL_INDEX_ITEM_ID,
    NATIONAL_INDEX_TABLE,
    NOT_APPLICABLE,
    REORDER_CANDIDATE,
    UNAVAILABLE,
    VERIFIED_SORTED,
    VERIFIED_UNSORTED,
    VERIFY_VALUES,
    classify_file,
    is_tribunal_year_item,
    list_djen_items,
    list_national_index_file,
    ranges_overlap,
    read_footer_stats,
    read_value_order,
    resolve_verify_values,
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

    def test_national_index_table_is_its_own_bucket_even_without_marker(self) -> None:
        # Issue #1470: "Classificar o indice nacional separadamente; nao
        # regenera-lo so porque nao tem o marcador novo." indice_processual
        # is a thin cross-source index (RFC 0014 M2), not a per-tribunal
        # comunicacoes/processos export -- the reorder-candidate contract
        # does not apply to it, so it must never fall into the generic
        # not_applicable or reorder_candidate buckets just because it lacks
        # the marker or has overlapping numero_processo ranges by design.
        result = classify_file(
            table_name=NATIONAL_INDEX_TABLE,
            has_conformant_marker=False,
            row_group_ranges=[("001", "090"), ("005", "099")],
            read_error=None,
        )
        assert result == NATIONAL_INDEX

    def test_national_index_read_error_is_still_unavailable(self) -> None:
        result = classify_file(
            table_name=NATIONAL_INDEX_TABLE,
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


class TestResolveVerifyValues:
    def test_passes_through_every_non_verify_values_classification_unchanged(self) -> None:
        # resolve_verify_values must never re-litigate a classification
        # classify_file already settled from footer stats -- it only ever
        # tightens the one bucket (VERIFY_VALUES) that footer stats alone
        # could not decide.
        for classification in (
            CONFORMANT,
            REORDER_CANDIDATE,
            NOT_APPLICABLE,
            UNAVAILABLE,
            NATIONAL_INDEX,
        ):
            assert resolve_verify_values(classification, order_result=True) == classification
            assert resolve_verify_values(classification, order_result=False) == classification
            assert resolve_verify_values(classification, order_result=None) == classification

    def test_confirmed_sorted_order_resolves_to_verified_sorted(self) -> None:
        assert resolve_verify_values(VERIFY_VALUES, order_result=True) == VERIFIED_SORTED

    def test_confirmed_inversion_resolves_to_verified_unsorted(self) -> None:
        assert resolve_verify_values(VERIFY_VALUES, order_result=False) == VERIFIED_UNSORTED

    def test_unreadable_order_stays_verify_values(self) -> None:
        # A failed value read is an unknown gap, not evidence either way --
        # same "never guess" rule classify_file already applies to a footer
        # read_error.
        assert resolve_verify_values(VERIFY_VALUES, order_result=None) == VERIFY_VALUES


class TestReadValueOrder:
    def test_detects_values_that_are_sorted_in_physical_file_order(self, tmp_path) -> None:
        path = tmp_path / "comunicacoes.parquet"
        con = duckdb.connect(":memory:")
        con.execute(
            "CREATE TABLE t AS "
            "SELECT lpad(i::VARCHAR, 4, '0') AS numero_processo FROM range(1, 3001) t(i)"
        )
        # Single row group by construction (no ROW_GROUP_SIZE override), the
        # exact shape that leaves classify_file unable to decide from footer
        # stats alone.
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET)")

        assert read_value_order(str(path)) is True

    def test_detects_a_real_inversion_in_physical_file_order(self, tmp_path) -> None:
        path = tmp_path / "comunicacoes.parquet"
        con = duckdb.connect(":memory:")
        con.execute(
            "CREATE TABLE t (numero_processo VARCHAR); "
            "INSERT INTO t VALUES ('001'), ('002'), ('000'), ('003')"
        )
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET)")

        assert read_value_order(str(path)) is False

    def test_missing_file_returns_none_not_a_crash(self, tmp_path) -> None:
        assert read_value_order(str(tmp_path / "does-not-exist.parquet")) is None


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


class TestListNationalIndexFile:
    def test_returns_the_indice_processual_file_from_the_dashboard_item(self) -> None:
        payload = {
            "files": [
                {"name": "sync-manifest.parquet"},
                {"name": "indice_processual.parquet"},
                {"name": "indice_processual.report.json"},
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert NATIONAL_INDEX_ITEM_ID in str(request.url)
            return httpx.Response(200, json=payload)

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            result = list_national_index_file(client)

        assert result is not None
        table_name, url = result
        assert table_name == NATIONAL_INDEX_TABLE
        assert url.endswith("indice_processual.parquet")
        assert NATIONAL_INDEX_ITEM_ID in url

    def test_returns_none_when_the_index_has_not_been_published_yet(self) -> None:
        payload = {"files": [{"name": "sync-manifest.parquet"}]}
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        with httpx.Client(transport=transport) as client:
            result = list_national_index_file(client)

        assert result is None


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
