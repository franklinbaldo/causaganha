"""Unit tests for ``scripts.backfill_probe._classify``.

This diagnostic script's entire purpose (per its own docstring) is to spot
drift between the manifest's recorded ``djen_raw`` and a live re-probe. Its
local ``_classify`` must agree with the canonical absent-code set in
``djen_backup.manifest.ABSENT_CODES`` -- otherwise rows written with the
``"no_publications"`` sentinel (DJEN's 200-Sem-comunicações response, per
CLAUDE.md) fall into a separate ``other:no_publications`` bucket instead of
``"absent"``, and get falsely reported as drift against a live probe.
"""

from __future__ import annotations

from scripts.backfill_probe import _classify


def test_classify_treats_no_publications_as_absent() -> None:
    assert _classify("no_publications") == "absent"


def test_classify_treats_genuine_not_found_as_absent() -> None:
    assert _classify("404") == "absent"
    assert _classify("400") == "absent"


def test_classify_available_on_200() -> None:
    assert _classify("200") == "available"


def test_classify_available_on_200_with_detail_suffix() -> None:
    """``djen_backup.manifest.interpret_djen_raw`` treats "200:<url>" as available too --

    a real value written by the legacy engine format (see
    tests/fixtures/manifest_contract_rows.csv and
    web/src/queries/site_status.qmd). Without this, a manifest row stored as
    "200:https://..." and a live re-probe returning bare "200" land in
    different _classify buckets ("other:200:..." vs "available") and
    _diff_label reports a false DRIFT for a row that is not actually drifting.
    """
    assert _classify("200:https://example.test/djen.zip") == "available"


def test_classify_rate_limited_on_403() -> None:
    assert _classify("403") == "rate-limited"


def test_classify_transient_on_timeout_and_network() -> None:
    assert _classify("timeout") == "transient"
    assert _classify("network") == "transient"


def test_classify_unknown_on_empty() -> None:
    assert _classify("") == "unknown"
