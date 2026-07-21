"""Tests for stj_acordaos.service — CKAN resource classification, skip/fail-fast.

Regression: the STJ dataset carries a non-JSON "dicionário de dados"
resource (format=CSV) that used to be blindly downloaded as ``.json`` and
later broke DuckDB's ``read_json`` during dedup/upload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from typer.testing import CliRunner

from stj_acordaos import service
from stj_acordaos.__main__ import app
from stj_acordaos.client import STJWAFBlockedError
from stj_acordaos.manifest import ManifestSTJ
from stj_acordaos.service import _already_uploaded, _classify_resource
from stj_acordaos.service import download_one as _download_one
from stj_acordaos.service import restore_manifest_best_effort as _restore_manifest_best_effort


if TYPE_CHECKING:
    from pathlib import Path


def test_zip_format_classified_as_zip() -> None:
    assert _classify_resource("ZIP", "https://example.org/x") == "zip"


def test_zip_url_suffix_classified_as_zip_even_without_format() -> None:
    assert _classify_resource("", "https://example.org/x.ZIP") == "zip"


def test_json_format_classified_as_json() -> None:
    assert _classify_resource("JSON", "https://example.org/x") == "json"


def test_json_url_suffix_classified_as_json_even_without_format() -> None:
    assert _classify_resource("", "https://example.org/x.json") == "json"


def test_csv_dictionary_resource_is_skipped_not_treated_as_json() -> None:
    assert _classify_resource("CSV", "https://example.org/dicionario-espelhodoacordao.csv") is None


def test_unknown_format_and_extension_is_skipped() -> None:
    assert _classify_resource("", "https://example.org/readme") is None


# ── _already_uploaded ──────────────────────────────────────────────────────


def test_already_uploaded_true_when_uploaded_and_unchanged(tmp_path: Path) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    manifest.upsert("a.zip", "zip", "2024-01-31", "uploaded", 10)
    assert _already_uploaded(manifest, "a.zip", "2024-01-31") is True


def test_already_uploaded_false_when_last_modified_changed(tmp_path: Path) -> None:
    """CKAN republished the resource — re-download even though it was uploaded before."""
    manifest = ManifestSTJ(tmp_path / "m.csv")
    manifest.upsert("a.zip", "zip", "2024-01-31", "uploaded", 10)
    assert _already_uploaded(manifest, "a.zip", "2024-02-15") is False


def test_already_uploaded_false_when_not_yet_uploaded(tmp_path: Path) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    manifest.upsert("a.zip", "zip", "2024-01-31", "", 10)
    assert _already_uploaded(manifest, "a.zip", "2024-01-31") is False


def test_already_uploaded_false_when_unknown(tmp_path: Path) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    assert _already_uploaded(manifest, "never-seen.zip", "2024-01-31") is False


# ── _download_one: skip, fail-fast, error discipline ────────────────────────


def _resource(**overrides: object) -> dict:
    base = {
        "url": "https://dadosabertos.web.stj.jus.br/x.zip",
        "name": "acordaos-2024",
        "format": "ZIP",
        "last_modified": "2024-01-31",
    }
    base.update(overrides)
    return base


def test_download_one_skips_no_url(tmp_path: Path) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    _download_one(_resource(url=""), manifest, tmp_path, tmp_path)
    assert manifest.get("acordaos-2024.zip") is None


def test_download_one_skips_unrecognized_format(tmp_path: Path) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    resource = _resource(format="CSV", url="https://x/dicionario.csv")
    _download_one(resource, manifest, tmp_path, tmp_path)
    assert len(manifest) == 0


def test_download_one_skips_already_uploaded_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    manifest.upsert("acordaos-2024.zip", "zip", "2024-01-31", "uploaded", 5)

    def _boom(*_args: object, **_kwargs: object) -> None:
        msg = "download_resource must not be called for an unchanged, uploaded entry"
        raise AssertionError(msg)

    monkeypatch.setattr("stj_acordaos.client.download_resource", _boom)
    _download_one(_resource(), manifest, tmp_path, tmp_path)
    # entry untouched — still the pre-existing uploaded state
    assert manifest.get("acordaos-2024.zip").n_registros == 5


def test_download_one_re_downloads_when_last_modified_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = ManifestSTJ(tmp_path / "m.csv")
    manifest.upsert("acordaos-2024.zip", "zip", "2024-01-31", "uploaded", 5)
    calls: list[str] = []
    monkeypatch.setattr(
        "stj_acordaos.client.download_resource", lambda url, _dest: calls.append(url)
    )
    monkeypatch.setattr("stj_acordaos.client.extract_zip", lambda *_a, **_k: [])

    _download_one(_resource(last_modified="2024-02-15"), manifest, tmp_path, tmp_path)

    assert calls == ["https://dadosabertos.web.stj.jus.br/x.zip"]
    # re-recorded as pending (ia_status reset) with the new last_modified
    entry = manifest.get("acordaos-2024.zip")
    assert entry.data_extracao == "2024-02-15"
    assert entry.ia_status == ""


def test_download_one_stj_waf_blocked_error_propagates_fail_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A confirmed WAF block must abort the whole run, not just this resource."""
    manifest = ManifestSTJ(tmp_path / "m.csv")
    request = httpx.Request("GET", "https://dadosabertos.web.stj.jus.br/x.zip")
    response = httpx.Response(403, request=request)

    def _blocked(*_args: object, **_kwargs: object) -> None:
        msg = "blocked"
        raise STJWAFBlockedError(msg, request=request, response=response)

    monkeypatch.setattr("stj_acordaos.client.download_resource", _blocked)
    with pytest.raises(STJWAFBlockedError):
        _download_one(_resource(), manifest, tmp_path, tmp_path)


# ── _restore_manifest_best_effort ────────────────────────────────────────


def test_restore_manifest_skips_when_local_copy_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = tmp_path / "stj-manifest.csv"
    manifest_path.write_text("arquivo,tipo\na.zip,zip\n")

    def _boom(_dest: Path) -> None:
        msg = "fetch_manifest must not be called when a local manifest already exists"
        raise AssertionError(msg)

    monkeypatch.setattr("stj_acordaos.archive.fetch_manifest", _boom)
    _restore_manifest_best_effort(manifest_path)  # must not raise


def test_restore_manifest_survives_transient_ia_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IA can 503 (not 404) for an item that was simply never created — must not crash.

    Regression: the first acceptance run of this branch died here — a brand
    new, never-uploaded IA item returned 503 from archive.org's download
    endpoint, and the uncaught HTTPStatusError aborted the entire download.
    """
    manifest_path = tmp_path / "stj-manifest.csv"
    request = httpx.Request("GET", "https://archive.org/download/stj-acordaos-primeira-secao/x")
    response = httpx.Response(503, request=request)

    def _flaky(_dest: Path) -> None:
        msg = "503"
        raise httpx.HTTPStatusError(msg, request=request, response=response)

    monkeypatch.setattr("stj_acordaos.archive.fetch_manifest", _flaky)

    _restore_manifest_best_effort(manifest_path)  # must not raise
    assert not manifest_path.exists()


# ── upload_all: ok must reflect every required artifact ──────────────────


def test_upload_all_ok_is_false_when_a_source_fails_even_if_parquet_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: a failed source upload must not be masked by a later, successful one.

    `ok` used to be reassigned by each source's upload and then overwritten
    by the parquet upload's own `ok` — so a failed ZIP/JSON upload silently
    disappeared as long as the parquet itself made it to IA.
    """
    data_dir = tmp_path / "data"
    zip_dir = data_dir / "zips"
    zip_dir.mkdir(parents=True)
    (zip_dir / "a.zip").write_bytes(b"fake")

    parquet_path = data_dir / "stj-acordaos.parquet"
    parquet_path.write_bytes(b"fake-parquet")  # pre-existing — dedup step is skipped
    manifest_path = data_dir / "stj-manifest.csv"

    def _fake_upload(path: Path, _ia_key: str, _ia_secret: str) -> bool:
        return path.name != "a.zip"  # the source fails; parquet + manifest succeed

    monkeypatch.setattr("stj_acordaos.archive.upload_parquet", _fake_upload)

    result = service.upload_all(data_dir, parquet_path, manifest_path, "k", "s")

    assert result.status == "done"
    assert result.ok is False


# ── upload: nothing-new-to-do must not be an error ───────────────────────

runner = CliRunner()


def test_upload_with_everything_already_uploaded_is_a_clean_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: this must be a clean no-op, not an upload error.

    A blank runner that skipped every download (all resources already
    uploaded+unchanged per the manifest) has neither fresh JSON files nor a
    local consolidated parquet — `dedup_acordaos` was never invoked, so
    there's nothing to re-dedupe, and the parquet was never restored from
    IA. IA already has the correct parquet from the run that produced it,
    so this is not "ERROR: No JSON files and no existing parquet to upload."
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    manifest_path = data_dir / "stj-manifest.csv"
    manifest = ManifestSTJ(manifest_path)
    manifest.upsert("20260531.json.json", "json", "2026-05-31", "uploaded", 12)
    manifest.upsert("stj-acordaos.parquet", "parquet", "", "uploaded", 0)
    manifest.save()

    def _boom(*_args: object, **_kwargs: object) -> bool:
        msg = "upload_parquet must not be called when there is nothing new"
        raise AssertionError(msg)

    monkeypatch.setattr("stj_acordaos.archive.upload_parquet", _boom)
    monkeypatch.setenv("IA_ACCESS_KEY", "k")
    monkeypatch.setenv("IA_SECRET_KEY", "s")

    result = runner.invoke(
        app,
        [
            "upload",
            "--data-dir",
            str(data_dir),
            "--parquet-path",
            str(data_dir / "stj-acordaos.parquet"),
            "--manifest-path",
            str(manifest_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Nothing new to upload" in result.output


def test_upload_with_pending_entries_but_no_local_data_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the manifest says something is genuinely pending but there's no
    local JSON and no local parquet to build one from, that IS an error —
    distinguishes the graceful no-op above from real data loss.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    manifest_path = data_dir / "stj-manifest.csv"
    manifest = ManifestSTJ(manifest_path)
    manifest.upsert("20260630.json.json", "json", "2026-06-30", "", 0)  # pending
    manifest.save()

    monkeypatch.setattr(
        "stj_acordaos.archive.upload_parquet",
        lambda *a, **k: (_ for _ in ()).throw(  # noqa: ARG005
            AssertionError("must not upload with nothing to send")
        ),
    )
    monkeypatch.setenv("IA_ACCESS_KEY", "k")
    monkeypatch.setenv("IA_SECRET_KEY", "s")

    result = runner.invoke(
        app,
        [
            "upload",
            "--data-dir",
            str(data_dir),
            "--parquet-path",
            str(data_dir / "stj-acordaos.parquet"),
            "--manifest-path",
            str(manifest_path),
        ],
    )

    assert result.exit_code != 0
    assert "No JSON files and no existing parquet" in result.output
