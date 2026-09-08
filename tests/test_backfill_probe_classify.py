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


def test_classify_rate_limited_on_403() -> None:
    assert _classify("403") == "rate-limited"


def test_classify_transient_on_timeout_and_network() -> None:
    assert _classify("timeout") == "transient"
    assert _classify("network") == "transient"


def test_classify_unknown_on_empty() -> None:
    assert _classify("") == "unknown"
