"""Tests for comparing an observed TCU Acórdãos CSV header against the product contract.

#984 requires comparing the schema observed in a real bulk file against the documented
dictionary "linha a linha" — surfacing gaps and extras rather than inventing or silently
dropping fields.
"""

from __future__ import annotations

from tcu_acordaos.ingest import REQUIRED_COLUMNS
from tcu_acordaos.schema_diff import diff_header


def test_diff_header_reports_no_gap_when_observed_matches_required() -> None:
    diff = diff_header(REQUIRED_COLUMNS)

    assert diff.missing == ()
    assert diff.extra == ()
    assert diff.is_compatible is True


def test_diff_header_reports_missing_required_columns() -> None:
    observed = REQUIRED_COLUMNS - {"VOTO", "RELATORIO"}

    diff = diff_header(observed)

    assert diff.missing == ("RELATORIO", "VOTO")
    assert diff.is_compatible is False


def test_diff_header_reports_extra_observed_columns_without_dropping_them() -> None:
    observed = set(REQUIRED_COLUMNS) | {"VISAOGERAL", "NUMATA", "ENTIDADE"}

    diff = diff_header(observed)

    assert diff.missing == ()
    assert diff.extra == ("ENTIDADE", "NUMATA", "VISAOGERAL")
    assert diff.is_compatible is True
