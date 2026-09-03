"""Tests for the pure report-assembly/decision logic of the #1012 identity investigation.

Only ``parse_header_line`` and ``build_identity_report`` are unit-tested here: they are the
parts of ``scripts/tcu_acordaos_identity_investigation.py`` with no network or filesystem I/O.
The rest of the script performs real range-request/full-download acquisition against the
official TCU portal for every year 1992-2016 (headers) and three representative years
including 2016 (full candidate-key analysis), and is run manually to produce
``docs/data/tcu-acordaos-identity-1992-2016.json`` — see #1012.
"""

from __future__ import annotations

import pytest

from scripts.tcu_acordaos_identity_investigation import (
    CANDIDATE_FIELDS,
    build_identity_report,
    candidate_key_name,
    parse_header_line,
)


def _full_year_evidence(source_url: str, sha256_char: str) -> dict:
    return {
        "source_url": source_url,
        "final_url": source_url,
        "acquired_at": "2026-09-03T00:00:00Z",
        "size_bytes": 1,
        "sha256": sha256_char * 64,
        "record_count": 3,
    }


def _report(*, null_rows: int = 0, colliding_values: int = 0, max_collision_size: int = 1) -> dict:
    return {
        "total_rows": 3,
        "null_rows": null_rows,
        "unique_values": 3 - null_rows - colliding_values,
        "colliding_values": colliding_values,
        "max_collision_size": max_collision_size,
        "is_stable": null_rows == 0 and colliding_values == 0,
    }


def test_parse_header_line_reads_pipe_delimited_quoted_columns() -> None:
    raw = '"TIPO"|"NUMACORDAO"|"ANOACORDAO"\n"ACORDAO"|"1"|"1995"\n'

    assert parse_header_line(raw) == ["TIPO", "NUMACORDAO", "ANOACORDAO"]


def test_candidate_key_name_joins_composite_fields_with_plus() -> None:
    assert candidate_key_name(("PROC", "ANOACORDAO")) == "PROC+ANOACORDAO"
    assert candidate_key_name(("NUMACORDAO",)) == "NUMACORDAO"


def test_build_identity_report_requires_2016_among_full_year_evidence() -> None:
    with pytest.raises(ValueError, match="2016"):
        build_identity_report(
            header_evidence={"1992": ["TIPO", "NUMACORDAO"]},
            full_year_evidence={"1992": _full_year_evidence("u1992", "a")},
            candidate_reports={"1992": {candidate_key_name(CANDIDATE_FIELDS[0]): _report()}},
        )


def test_build_identity_report_declares_ineligible_when_no_candidate_stable_everywhere() -> None:
    full_year_evidence = {
        "1992": _full_year_evidence("u1992", "a"),
        "2016": _full_year_evidence("u2016", "b"),
    }
    # NUMACORDAO alone collides across colegiados (the documented #1012 risk); PROC alone is
    # stable in 1992 but collides in 2016 (multiple acórdãos per processo over time).
    candidate_reports = {
        "1992": {
            candidate_key_name(("NUMACORDAO",)): _report(colliding_values=1, max_collision_size=2),
            candidate_key_name(("PROC",)): _report(),
        },
        "2016": {
            candidate_key_name(("NUMACORDAO",)): _report(colliding_values=1, max_collision_size=2),
            candidate_key_name(("PROC",)): _report(colliding_values=1, max_collision_size=2),
        },
    }

    report = build_identity_report(
        header_evidence={"1992": ["TIPO"], "2016": ["TIPO"]},
        full_year_evidence=full_year_evidence,
        candidate_reports=candidate_reports,
    )

    assert report["decision"]["status"] == "ineligible"
    assert report["decision"]["accepted_candidate"] is None


def test_build_identity_report_accepts_first_candidate_stable_in_every_full_year() -> None:
    full_year_evidence = {
        "1992": _full_year_evidence("u1992", "a"),
        "2016": _full_year_evidence("u2016", "b"),
    }
    numacordao = candidate_key_name(("NUMACORDAO",))
    proc = candidate_key_name(("PROC",))
    candidate_reports = {
        "1992": {numacordao: _report(colliding_values=1, max_collision_size=2), proc: _report()},
        "2016": {numacordao: _report(colliding_values=1, max_collision_size=2), proc: _report()},
    }

    report = build_identity_report(
        header_evidence={"1992": ["TIPO"], "2016": ["TIPO"]},
        full_year_evidence=full_year_evidence,
        candidate_reports=candidate_reports,
    )

    assert report["decision"]["status"] == "accepted"
    assert report["decision"]["accepted_candidate"] == proc


def test_build_identity_report_prefers_earlier_candidate_even_if_a_later_one_is_also_stable() -> (
    None
):
    full_year_evidence = {
        "1992": _full_year_evidence("u1992", "a"),
        "2016": _full_year_evidence("u2016", "b"),
    }
    numacordao = candidate_key_name(CANDIDATE_FIELDS[0])
    another_stable = candidate_key_name(CANDIDATE_FIELDS[-1])
    candidate_reports = {
        "1992": {numacordao: _report(), another_stable: _report()},
        "2016": {numacordao: _report(), another_stable: _report()},
    }

    report = build_identity_report(
        header_evidence={"1992": ["TIPO"], "2016": ["TIPO"]},
        full_year_evidence=full_year_evidence,
        candidate_reports=candidate_reports,
    )

    assert report["decision"]["accepted_candidate"] == numacordao


def test_build_identity_report_includes_header_and_full_year_evidence_verbatim() -> None:
    full_year_evidence = {
        "1992": _full_year_evidence("u1992", "a"),
        "2016": _full_year_evidence("u2016", "b"),
    }
    proc = candidate_key_name(("PROC",))
    candidate_reports = {
        "1992": {proc: _report()},
        "2016": {proc: _report()},
    }

    report = build_identity_report(
        header_evidence={"1992": ["TIPO", "PROC"], "2016": ["KEY", "TIPO", "PROC"]},
        full_year_evidence=full_year_evidence,
        candidate_reports=candidate_reports,
    )

    assert report["header_evidence"] == {
        "1992": ["TIPO", "PROC"],
        "2016": ["KEY", "TIPO", "PROC"],
    }
    assert report["full_year_evidence"] == full_year_evidence
    assert report["window"] == {"first_year": 1992, "last_year": 2016}
