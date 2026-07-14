"""Tests for tjro_juris.__main__ — incremental crawl bounds, manifest restore, skip logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import pyarrow.parquet as pq
import pytest
import typer

from tjro_juris.__main__ import (
    _crawl_bounds,
    _load_manifest,
    _rows_to_parquet,
    _should_skip_window,
    _to_row,
)
from tjro_juris.manifest import ManifestJuris, ManifestJurisEntry


if TYPE_CHECKING:
    from pathlib import Path


# ── _to_row / _rows_to_parquet ───────────────────────────────────────────

_FULL_CRAWLER_DOC = {
    "id_documento": 42,
    "nr_processo": "00042-11.2024.8.22.0001",
    "tipo": "ACÓRDÃO",
    "classe_judicial": "Apelação Cível",
    "orgao": "1ª Câmara Cível",
    "relator": "Des. Fulano",
    "sistema_origem": "pje2instancia",
    "data_julgamento": "2024-03-15",
    "texto_limpo": "EMENTA: teste",
    "url_portal": "https://juris.tjro.jus.br/jurisprudencia/?id=42",
    "extraido_em": "2026-07-14T00:00:00+00:00",
    "id_processo": 999,
    "cd_assunto_trf": "3372",
    "ds_assunto_trf": "Homicídio Qualificado",
    "cd_classe_judicial": "417",
    "nivel_sigilo_processo": 0,
    "grau_jurisdicao": 2,
    "ds_md5_documento": "abc123",
    "id_orgao_julgador": 22,
    "id_orgao_julgador_colegiado": 12,
}


def test_to_row_maps_new_metadata_fields() -> None:
    row = _to_row(_FULL_CRAWLER_DOC)
    assert row["id_processo"] == 999
    assert row["cd_assunto_trf"] == "3372"
    assert row["ds_assunto_trf"] == "Homicídio Qualificado"
    assert row["cd_classe_judicial"] == "417"
    assert row["nivel_sigilo_processo"] == 0
    assert row["grau_jurisdicao"] == 2
    assert row["ds_md5_documento"] == "abc123"
    assert row["id_orgao_julgador"] == 22
    assert row["id_orgao_julgador_colegiado"] == 12


def test_to_row_defaults_new_fields_when_missing() -> None:
    row = _to_row({"data_julgamento": "2024-01-01"})
    assert row["id_processo"] is None
    assert row["cd_assunto_trf"] == ""
    assert row["nivel_sigilo_processo"] is None
    assert row["id_orgao_julgador"] is None


def test_rows_to_parquet_round_trips_new_int_and_string_fields(tmp_path: Path) -> None:
    """New int64 fields (nivel_sigilo_processo etc.) must not get str()-coerced,
    and a None int field must round-trip as a real parquet null, not "None".
    """
    row = _to_row(_FULL_CRAWLER_DOC)
    missing_row = _to_row({"data_julgamento": "2024-01-01"})
    out = tmp_path / "test.parquet"
    _rows_to_parquet([row, missing_row], out)

    table = pq.read_table(out)
    data = table.to_pylist()
    assert data[0]["id_processo"] == 999
    assert data[0]["nivel_sigilo_processo"] == 0
    assert data[0]["id_orgao_julgador_colegiado"] == 12
    assert data[0]["ds_assunto_trf"] == "Homicídio Qualificado"
    assert data[1]["id_processo"] is None
    assert data[1]["nivel_sigilo_processo"] is None
    assert data[1]["cd_assunto_trf"] == ""

    schema_types = {f.name: f.type for f in table.schema}
    assert str(schema_types["id_processo"]) == "int64"
    assert str(schema_types["nivel_sigilo_processo"]) == "int64"
    assert str(schema_types["ds_assunto_trf"]) == "string"


# ── _crawl_bounds ────────────────────────────────────────────────────────


def test_crawl_bounds_defaults_to_full_history() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(None, None, None, now) == (2010, None, None)


def test_crawl_bounds_mes_narrows_to_a_single_month() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(None, "2026-07", None, now) == (2026, "2026-07", "2026-07")


def test_crawl_bounds_mes_rejects_bad_format() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    with pytest.raises(typer.BadParameter, match="AAAA-MM"):
        _crawl_bounds(None, "2026-13", None, now)
    with pytest.raises(typer.BadParameter, match="AAAA-MM"):
        _crawl_bounds(None, "not-a-month", None, now)


def test_crawl_bounds_mes_and_ano_are_mutually_exclusive() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    with pytest.raises(typer.BadParameter, match="mutually exclusive"):
        _crawl_bounds(2026, "2026-07", None, now)


def test_crawl_bounds_ano_past_year_ends_in_december() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(2020, None, None, now) == (2020, "2020-12", None)


def test_crawl_bounds_ano_current_year_ends_at_current_month() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(2026, None, None, now) == (2026, "2026-07", None)


def test_crawl_bounds_desde_ano_overrides_default_start() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    assert _crawl_bounds(None, None, 1988, now) == (1988, None, None)


def test_crawl_bounds_desde_ano_mutually_exclusive_with_ano() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    with pytest.raises(typer.BadParameter, match="mutually exclusive"):
        _crawl_bounds(2020, None, 1988, now)


def test_crawl_bounds_desde_ano_mutually_exclusive_with_mes() -> None:
    now = datetime(2026, 7, 12, tzinfo=UTC)
    with pytest.raises(typer.BadParameter, match="mutually exclusive"):
        _crawl_bounds(None, "2026-07", 1988, now)


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


def test_load_manifest_survives_transient_ia_error_starts_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IA can 503 (not 404) for an item that was simply never created — must not crash.

    Regression: the first acceptance run of this branch died here — a brand
    new, never-uploaded IA item returned 503 from archive.org's download
    endpoint, and the uncaught HTTPStatusError aborted the entire crawl.
    """
    request = httpx.Request("GET", "https://archive.org/download/tjro-juris/x.csv")
    response = httpx.Response(503, request=request)

    def _flaky(_dest: Path) -> bool:
        msg = "503"
        raise httpx.HTTPStatusError(msg, request=request, response=response)

    monkeypatch.setattr("tjro_juris.__main__.ia_archive.download_manifest", _flaky)

    manifest = _load_manifest(tmp_path)  # must not raise

    assert manifest.all_entries() == []
