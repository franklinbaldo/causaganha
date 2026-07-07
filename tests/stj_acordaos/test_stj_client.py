"""Tests for stj_acordaos.client — CKAN payload parsing, HTTP error discipline, safe ZIP extract.

Error discipline (CLAUDE.md): 403 and timeouts are transient transport
failures — they must RAISE, never silently degrade into "no resources"
(the analogue of djen-backup's "403 is never absent").
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from stj_acordaos.client import DATASET_API_URL, download_resource, extract_zip, get_resource_list


if TYPE_CHECKING:
    from pathlib import Path


# ── get_resource_list ────────────────────────────────────────────────────


def test_get_resource_list_parses_ckan_payload() -> None:
    payload = {
        "success": True,
        "result": {
            "resources": [
                {"url": "https://stj.example/a.zip", "name": "a", "format": "ZIP"},
                {"url": "https://stj.example/b.json", "name": "b", "format": "JSON"},
            ]
        },
    }
    with respx.mock() as router:
        router.get(DATASET_API_URL).respond(200, json=payload)
        resources = get_resource_list()

    assert [r["name"] for r in resources] == ["a", "b"]


def test_get_resource_list_empty_resources_is_empty_list() -> None:
    with respx.mock() as router:
        router.get(DATASET_API_URL).respond(200, json={"success": True, "result": {}})
        assert get_resource_list() == []


def test_get_resource_list_success_false_raises_runtime_error() -> None:
    with respx.mock() as router:
        router.get(DATASET_API_URL).respond(
            200, json={"success": False, "error": {"message": "boom"}}
        )
        with pytest.raises(RuntimeError, match="success=false"):
            get_resource_list()


def test_get_resource_list_403_raises_never_returns_empty() -> None:
    """A 403 (WAF/rate-limit) must surface as an error — not an empty dataset."""
    with respx.mock() as router:
        router.get(DATASET_API_URL).respond(403)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            get_resource_list()
    assert exc_info.value.response.status_code == 403


def test_get_resource_list_timeout_propagates() -> None:
    """Timeouts must propagate — the caller decides on retry, never 'absent'."""
    with respx.mock() as router:
        router.get(DATASET_API_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))
        with pytest.raises(httpx.ConnectTimeout):
            get_resource_list()


def test_get_resource_list_500_raises() -> None:
    with respx.mock() as router:
        router.get(DATASET_API_URL).respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            get_resource_list()


# ── download_resource ────────────────────────────────────────────────────


def test_download_resource_writes_bytes_to_dest(tmp_path: Path) -> None:
    dest = tmp_path / "nested" / "file.zip"
    with respx.mock() as router:
        router.get("https://stj.example/file.zip").respond(200, content=b"PK-payload")
        download_resource("https://stj.example/file.zip", dest)

    assert dest.read_bytes() == b"PK-payload"


def test_download_resource_404_raises_and_writes_nothing(tmp_path: Path) -> None:
    dest = tmp_path / "file.zip"
    with respx.mock() as router:
        router.get("https://stj.example/file.zip").respond(404)
        with pytest.raises(httpx.HTTPStatusError):
            download_resource("https://stj.example/file.zip", dest)

    assert not dest.exists()


# ── extract_zip ──────────────────────────────────────────────────────────


def _make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)


def test_extract_zip_extracts_only_json_members(tmp_path: Path) -> None:
    zip_path = tmp_path / "in.zip"
    _make_zip(
        zip_path,
        {
            "a.json": b'{"id": 1}',
            "sub/b.json": b'{"id": 2}',
            "readme.txt": b"nope",
        },
    )
    dest = tmp_path / "out"
    extracted = extract_zip(zip_path, dest)

    assert sorted(p.name for p in extracted) == ["a.json", "b.json"]
    # Nested member is flattened into dest, not extracted into a subdir
    assert (dest / "b.json").read_bytes() == b'{"id": 2}'
    assert not (dest / "readme.txt").exists()


def test_extract_zip_rejects_path_traversal_and_absolute_paths(tmp_path: Path) -> None:
    zip_path = tmp_path / "evil.zip"
    _make_zip(
        zip_path,
        {
            "../escape.json": b"{}",
            "/abs.json": b"{}",
            "ok.json": b'{"id": 1}',
        },
    )
    dest = tmp_path / "out"
    extracted = extract_zip(zip_path, dest)

    assert [p.name for p in extracted] == ["ok.json"]
    assert not (tmp_path / "escape.json").exists()
    assert not (dest / "escape.json").exists()


def test_extract_zip_empty_archive(tmp_path: Path) -> None:
    zip_path = tmp_path / "empty.zip"
    _make_zip(zip_path, {})
    assert extract_zip(zip_path, tmp_path / "out") == []
