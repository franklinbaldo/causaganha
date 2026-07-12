"""Tests for stj_acordaos.__main__ — CKAN resource classification, skip/fail-fast.

Regression: the STJ dataset carries a non-JSON "dicionário de dados"
resource (format=CSV) that used to be blindly downloaded as ``.json`` and
later broke DuckDB's ``read_json`` during dedup/upload.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from stj_acordaos.__main__ import _already_uploaded, _classify_resource, _download_one
from stj_acordaos.client import STJWAFBlockedError
from stj_acordaos.manifest import ManifestSTJ


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

    monkeypatch.setattr("stj_acordaos.__main__.download_resource", _boom)
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
        "stj_acordaos.__main__.download_resource", lambda url, _dest: calls.append(url)
    )
    monkeypatch.setattr("stj_acordaos.__main__.extract_zip", lambda *_a, **_k: [])

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

    monkeypatch.setattr("stj_acordaos.__main__.download_resource", _blocked)
    with pytest.raises(STJWAFBlockedError):
        _download_one(_resource(), manifest, tmp_path, tmp_path)
