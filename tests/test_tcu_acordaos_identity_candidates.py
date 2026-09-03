"""Tests for evaluating candidate identity fields on TCU Acórdãos rows lacking ``KEY``.

#1012 needs to test candidate identity fields (``PROC``, ``NUMACORDAO``, ``ANOACORDAO``,
``COLEGIADO`` and composites of these) against real 1992-2016 bulk files, which predate the
official ``KEY`` column. ``tcu_acordaos.ingest.load_csv`` intentionally rejects any file
missing a documented required column (including ``KEY``), so it cannot even open those
files. This module adds a raw loader that skips that validation, plus a report that measures
null rates and collisions per candidate field/composite — the evidence #1012 asks for before
declaring any pre-2017 identity stable.

These tests exercise the tool's own correctness with small synthetic fixtures; they are not
themselves the real 1992-2016 investigation #1012 requires (that needs the actual official
bulk files) and must not be read as such.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tcu_acordaos.identity_candidates import analyze_key_candidates, load_csv_raw


def _write_csv(tmp_path: Path, header: list[str], rows: list[list[str]]) -> Path:
    path = tmp_path / "acordaos.csv"
    lines = ["|".join(f'"{cell}"' for cell in header)]
    lines.extend("|".join(f'"{cell}"' for cell in row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return path


def test_load_csv_raw_reads_pre_2017_header_without_key(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        ["TIPO", "NUMACORDAO", "ANOACORDAO", "COLEGIADO", "PROC"],
        [["ACORDAO", "1", "1995", "Plenario", "001.000/1995-0"]],
    )

    rows = load_csv_raw(path)

    assert rows == [
        {
            "TIPO": "ACORDAO",
            "NUMACORDAO": "1",
            "ANOACORDAO": "1995",
            "COLEGIADO": "Plenario",
            "PROC": "001.000/1995-0",
        }
    ]


def test_load_csv_raw_does_not_require_required_columns(tmp_path: Path) -> None:
    # ingest.load_csv would reject this file outright for lacking KEY/TITULO/etc; the raw
    # loader exists precisely so header-incomplete historical files can still be inspected.
    path = _write_csv(tmp_path, ["NUMACORDAO", "ANOACORDAO"], [["10", "1998"]])

    rows = load_csv_raw(path)

    assert rows == [{"NUMACORDAO": "10", "ANOACORDAO": "1998"}]


def test_analyze_key_candidates_reports_stable_unique_field() -> None:
    rows = [
        {"NUMACORDAO": "1", "ANOACORDAO": "1995"},
        {"NUMACORDAO": "2", "ANOACORDAO": "1995"},
        {"NUMACORDAO": "3", "ANOACORDAO": "1995"},
    ]

    reports = analyze_key_candidates(rows, [("NUMACORDAO",)])
    report = reports[("NUMACORDAO",)]

    assert report.total_rows == 3
    assert report.null_rows == 0
    assert report.colliding_values == 0
    assert report.unique_values == 3
    assert report.is_stable is True


def test_analyze_key_candidates_reports_null_rows_without_crashing() -> None:
    rows = [
        {"PROC": "001.000/1995-0"},
        {"PROC": ""},
        {"PROC": "  "},
    ]

    reports = analyze_key_candidates(rows, [("PROC",)])
    report = reports[("PROC",)]

    assert report.total_rows == 3
    assert report.null_rows == 2
    assert report.is_stable is False


def test_analyze_key_candidates_reports_collisions_for_non_unique_field() -> None:
    # NUMACORDAO alone repeats across different colegiados/years in the real corpus (per
    # #1012's stated risk) — this is exactly the case the report must surface as unstable.
    rows = [
        {"NUMACORDAO": "1", "COLEGIADO": "Plenario"},
        {"NUMACORDAO": "1", "COLEGIADO": "Primeira Camara"},
        {"NUMACORDAO": "2", "COLEGIADO": "Plenario"},
    ]

    reports = analyze_key_candidates(rows, [("NUMACORDAO",)])
    report = reports[("NUMACORDAO",)]

    assert report.colliding_values == 1
    assert report.max_collision_size == 2
    assert report.is_stable is False


def test_analyze_key_candidates_supports_composite_fields() -> None:
    # A composite candidate is only as good as all of its parts together; one row missing
    # either component makes that row null for the composite, not silently half-keyed.
    rows = [
        {"PROC": "001.000/1995-0", "ANOACORDAO": "1995"},
        {"PROC": "001.000/1995-0", "ANOACORDAO": "1996"},
        {"PROC": "002.000/1995-0", "ANOACORDAO": ""},
    ]

    reports = analyze_key_candidates(rows, [("PROC", "ANOACORDAO")])
    report = reports[("PROC", "ANOACORDAO")]

    assert report.total_rows == 3
    assert report.null_rows == 1
    assert report.unique_values == 2
    assert report.colliding_values == 0
    assert report.is_stable is False  # null_rows > 0 still blocks stability


def test_analyze_key_candidates_evaluates_every_requested_candidate_independently() -> None:
    rows = [
        {"NUMACORDAO": "1", "PROC": "001.000/1995-0"},
        {"NUMACORDAO": "1", "PROC": "002.000/1995-0"},
    ]

    reports = analyze_key_candidates(rows, [("NUMACORDAO",), ("PROC",)])

    assert set(reports) == {("NUMACORDAO",), ("PROC",)}
    assert reports[("NUMACORDAO",)].is_stable is False
    assert reports[("PROC",)].is_stable is True


def test_analyze_key_candidates_rejects_empty_candidate_list() -> None:
    with pytest.raises(ValueError, match="candidate_fields"):
        analyze_key_candidates([{"PROC": "x"}], [])
