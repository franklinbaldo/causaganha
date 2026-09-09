"""Tests for datajud.manifest — CSV roundtrip and incremental refresh logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from datajud.manifest import HEADER, STATUS_ERRO, STATUS_OK, ManifestDataJud, ManifestFormatError


if TYPE_CHECKING:
    from pathlib import Path


CNJ = "00000010220248220001"


def test_load_local_missing_column_raises_manifest_format_error(tmp_path: Path) -> None:
    path = tmp_path / "datajud-manifest.csv"
    path.write_text("tribunal,docs,consultado_em,status\ntjro,3,,ok\n", encoding="utf-8")

    with pytest.raises(ManifestFormatError, match="cnj"):
        ManifestDataJud.load_local(path)


def test_load_local_non_numeric_docs_raises_manifest_format_error(tmp_path: Path) -> None:
    path = tmp_path / "datajud-manifest.csv"
    path.write_text(f"{HEADER}\n{CNJ},tjro,not-a-number,,ok\n", encoding="utf-8")

    with pytest.raises(ManifestFormatError):
        ManifestDataJud.load_local(path)


def test_roundtrip_preserves_entries(tmp_path: Path):
    manifest = ManifestDataJud()
    manifest.upsert(CNJ, "tjro", docs=3, status=STATUS_OK)
    manifest.upsert("00000020320248220002", "TJRO", docs=0, status=STATUS_ERRO)
    path = tmp_path / "datajud-manifest.csv"
    manifest.save_local(path)

    loaded = ManifestDataJud.load_local(path)
    assert len(loaded) == 2
    entry = loaded.get(CNJ, "tjro")
    assert entry is not None
    assert entry.docs == 3
    assert entry.status == STATUS_OK
    assert entry.consultado_em  # stamped by upsert
    # tribunal key is case-insensitive (stored lowercase)
    assert loaded.get("00000020320248220002", "tjro") is not None


def test_roundtrip_preserves_a_comma_in_status(tmp_path: Path):
    """save_local must escape commas, not just join fields with them.

    status is normally a controlled enum ("ok"/"erro"/"") today, but the
    on-disk format contract must not silently corrupt any value it is
    asked to persist -- the reader (csv.DictReader) already expects real
    CSV quoting, so the writer must produce it.
    """
    manifest = ManifestDataJud()
    manifest.upsert(CNJ, "tjro", docs=3, status=STATUS_OK)
    entry = manifest.get(CNJ, "tjro")
    assert entry is not None
    entry.status = "erro, timeout"
    path = tmp_path / "datajud-manifest.csv"
    manifest.save_local(path)

    loaded = ManifestDataJud.load_local(path)
    reloaded = loaded.get(CNJ, "tjro")
    assert reloaded is not None
    assert reloaded.status == "erro, timeout"


def test_load_missing_file_is_empty(tmp_path: Path):
    manifest = ManifestDataJud.load_local(tmp_path / "nope.csv")
    assert len(manifest) == 0


def test_needs_refresh_when_never_consulted():
    manifest = ManifestDataJud()
    assert manifest.needs_refresh(CNJ, "tjro", max_age_days=30) is True


def test_needs_refresh_false_for_fresh_ok_entry():
    manifest = ManifestDataJud()
    manifest.upsert(CNJ, "tjro", docs=2, status=STATUS_OK)
    assert manifest.needs_refresh(CNJ, "tjro", max_age_days=30) is False


def test_needs_refresh_true_for_errored_entry():
    manifest = ManifestDataJud()
    manifest.upsert(CNJ, "tjro", docs=0, status=STATUS_ERRO)
    assert manifest.needs_refresh(CNJ, "tjro", max_age_days=30) is True


def test_needs_refresh_true_for_stale_entry():
    manifest = ManifestDataJud()
    manifest.upsert(CNJ, "tjro", docs=2, status=STATUS_OK)
    entry = manifest.get(CNJ, "tjro")
    assert entry is not None
    entry.consultado_em = (datetime.now(UTC) - timedelta(days=45)).isoformat(timespec="seconds")
    assert manifest.needs_refresh(CNJ, "tjro", max_age_days=30) is True
    assert manifest.needs_refresh(CNJ, "tjro", max_age_days=90) is False


def test_needs_refresh_true_for_unparseable_timestamp():
    manifest = ManifestDataJud()
    manifest.upsert(CNJ, "tjro", docs=2, status=STATUS_OK)
    entry = manifest.get(CNJ, "tjro")
    assert entry is not None
    entry.consultado_em = "not-a-date"
    assert manifest.needs_refresh(CNJ, "tjro", max_age_days=30) is True
