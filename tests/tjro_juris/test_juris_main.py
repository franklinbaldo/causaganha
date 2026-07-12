"""Tests for tjro_juris.__main__ — incremental crawl bounds, manifest restore, skip logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import typer

from tjro_juris.__main__ import _crawl_bounds, _load_manifest, _should_skip_window
from tjro_juris.manifest import ManifestJuris, ManifestJurisEntry


if TYPE_CHECKING:
    from pathlib import Path


# ── _crawl_bounds ────────────────────────────────────────────────────────


def test_crawl_bounds_defaults_to_full_history() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(None, None, now) == (2010, None, None)


def test_crawl_bounds_mes_narrows_to_a_single_month() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(None, "2026-07", now) == (2026, "2026-07", "2026-07")


def test_crawl_bounds_mes_rejects_bad_format() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    with pytest.raises(typer.BadParameter, match="AAAA-MM"):
        _crawl_bounds(None, "2026-13", now)
    with pytest.raises(typer.BadParameter, match="AAAA-MM"):
        _crawl_bounds(None, "not-a-month", now)


def test_crawl_bounds_mes_and_ano_are_mutually_exclusive() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    with pytest.raises(typer.BadParameter, match="mutually exclusive"):
        _crawl_bounds(2026, "2026-07", now)


def test_crawl_bounds_ano_past_year_ends_in_december() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(2020, None, now) == (2020, "2020-12", None)


def test_crawl_bounds_ano_current_year_ends_at_current_month() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(2026, None, now) == (2026, "2026-07", None)


# ── _should_skip_window ──────────────────────────────────────────────────


def _manifest_with(tipo: str, mes_ano: str, ia_status: str) -> ManifestJuris:
    manifest = ManifestJuris()
    manifest.upsert(ManifestJurisEntry(tipo=tipo, mes_ano=mes_ano, ia_status=ia_status, n_docs=1))
    return manifest


def test_should_skip_window_true_for_uploaded_past_month() -> None:
    manifest = _manifest_with("ACÓRDÃO", "2026-06", "uploaded")
    assert _should_skip_window(manifest, "2026-07", "ACÓRDÃO", "2026-06") is True


def test_should_skip_window_false_for_pending_past_month() -> None:
    """Crawled but not yet uploaded — must be re-crawled, not skipped."""
    manifest = _manifest_with("ACÓRDÃO", "2026-06", "")
    assert _should_skip_window(manifest, "2026-07", "ACÓRDÃO", "2026-06") is False


def test_should_skip_window_false_for_unknown_window() -> None:
    manifest = ManifestJuris()
    assert _should_skip_window(manifest, "2026-07", "ACÓRDÃO", "2026-06") is False


def test_should_skip_window_never_skips_the_current_month_even_if_uploaded() -> None:
    """JURIS keeps publishing into the open month — always re-crawl it."""
    manifest = _manifest_with("ACÓRDÃO", "2026-07", "uploaded")
    assert _should_skip_window(manifest, "2026-07", "ACÓRDÃO", "2026-07") is False


def test_should_skip_window_never_skips_a_future_month() -> None:
    manifest = _manifest_with("ACÓRDÃO", "2026-08", "uploaded")
    assert _should_skip_window(manifest, "2026-07", "ACÓRDÃO", "2026-08") is False


# ── _load_manifest (blank-runner restore from IA) ────────────────────────


def test_load_manifest_restores_from_ia_when_local_copy_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []

    def _fake_download(dest: Path) -> bool:
        calls.append(dest)
        dest.write_text("tipo,mes_ano,ia_status,n_docs,updated_at\nVOTO,2026-01,uploaded,3,\n")
        return True

    monkeypatch.setattr("tjro_juris.__main__.ia_archive.download_manifest", _fake_download)

    manifest = _load_manifest(tmp_path)

    assert len(calls) == 1
    entry = manifest.get("VOTO", "2026-01")
    assert entry is not None
    assert entry.ia_status == "uploaded"


def test_load_manifest_skips_restore_when_local_copy_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "tjro-juris-manifest.csv").write_text(
        "tipo,mes_ano,ia_status,n_docs,updated_at\nEMENTA,2026-02,uploaded,1,\n"
    )

    def _boom(_dest: Path) -> bool:
        msg = "download_manifest must not be called when a local manifest already exists"
        raise AssertionError(msg)

    monkeypatch.setattr("tjro_juris.__main__.ia_archive.download_manifest", _boom)

    manifest = _load_manifest(tmp_path)
    assert manifest.get("EMENTA", "2026-02") is not None


def test_load_manifest_starts_empty_when_ia_has_no_manifest_either(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tjro_juris.__main__.ia_archive.download_manifest", lambda _dest: False)
    manifest = _load_manifest(tmp_path)
    assert manifest.all_entries() == []
