"""Unit tests for the streaming ZIP → NDJSON extractor."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import httpx
import pytest
import respx

from causaganha.consolidate import zip_processor
from causaganha.consolidate.zip_processor import (
    DownloadTooLargeError,
    ZipBudgetExceededError,
    download_zip,
    stream_zip_to_ndjson,
)


def _make_zip(path: Path, files: dict[str, object]) -> None:
    """Write a ZIP with the given {filename: content} entries."""
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            if isinstance(content, (dict, list)):
                data = json.dumps(content)
            else:
                data = content
            zf.writestr(name, data)


def test_stream_extracts_top_level_array() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "a.json": [
                    {"id": 1, "data_disponibilizacao": "2026-04-01"},
                    {"id": 2, "data_disponibilizacao": "2026-04-01"},
                    {"id": 3, "data_disponibilizacao": "2026-04-01"},
                ]
            },
        )

        count = stream_zip_to_ndjson(zip_path, out, "TJSP")

        assert count == 3
        lines = out.read_text().splitlines()
        assert len(lines) == 3
        rec = json.loads(lines[0])
        assert rec["id"] == 1
        assert rec["data_disponibilizacao"] == "2026-04-01"
        assert rec["_tribunal"] == "TJSP"


def test_stream_extracts_items_wrapper() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "a.json": {
                    "items": [{"id": 1, "data_disponibilizacao": "2026-04-01"}],
                    "status": "ok",
                }
            },
        )

        count = stream_zip_to_ndjson(zip_path, out, "TRT18")

        assert count == 1
        rec = json.loads(out.read_text().strip())
        assert rec["id"] == 1
        assert rec["_tribunal"] == "TRT18"


def test_stream_extracts_single_object() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "a.json": {
                    "id": 42,
                    "texto": "foo",
                    "data_disponibilizacao": "2026-04-01",
                }
            },
        )

        count = stream_zip_to_ndjson(zip_path, out, "TJCE")

        assert count == 1
        rec = json.loads(out.read_text().strip())
        assert rec["id"] == 42
        assert rec["texto"] == "foo"
        assert rec["_tribunal"] == "TJCE"


def test_stream_skips_non_json_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "readme.txt": "ignore me",
                "data.json": [{"id": 1, "data_disponibilizacao": "2026-04-01"}],
            },
        )

        count = stream_zip_to_ndjson(zip_path, out, "TJSP")

        assert count == 1


def test_stream_handles_malformed_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "broken.json": "{not valid json",
                "good.json": [{"id": 1, "data_disponibilizacao": "2026-04-01"}],
            },
        )

        count = stream_zip_to_ndjson(zip_path, out, "TJSP")

        assert count == 1


def test_stream_handles_bad_zip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "not_a_zip.zip"
        out = Path(tmpdir) / "out.ndjson"
        zip_path.write_bytes(b"garbage")

        count = stream_zip_to_ndjson(zip_path, out, "TJSP")

        assert count == 0


def test_stream_combines_multiple_json_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "a.json": [{"id": 1, "data_disponibilizacao": "2026-04-01"}],
                "b.json": [
                    {"id": 2, "data_disponibilizacao": "2026-04-01"},
                    {"id": 3, "data_disponibilizacao": "2026-04-01"},
                ],
                "c.json": {"items": [{"id": 4, "data_disponibilizacao": "2026-04-01"}]},
            },
        )

        count = stream_zip_to_ndjson(zip_path, out, "TRT4")

        assert count == 4
        lines = out.read_text().splitlines()
        ids = sorted(json.loads(line)["id"] for line in lines)
        assert ids == [1, 2, 3, 4]
        # All records must carry the tribunal stamp
        tribunals = {json.loads(line)["_tribunal"] for line in lines}
        assert tribunals == {"TRT4"}


def test_stream_rejects_zip_bomb_by_member_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """TM-05: a ZIP with far more members than any real DJEN bundle is a bomb, not data."""
    monkeypatch.setattr(zip_processor, "MAX_ZIP_MEMBERS", 3)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {f"{i}.json": [{"id": i, "data_disponibilizacao": "2026-04-01"}] for i in range(4)},
        )

        with pytest.raises(ZipBudgetExceededError, match="members"):
            stream_zip_to_ndjson(zip_path, out, "TJSP")


def test_stream_rejects_member_over_uncompressed_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """A single declared-size member above budget must fail before it is loaded."""
    monkeypatch.setattr(zip_processor, "MAX_MEMBER_UNCOMPRESSED_BYTES", 100)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        big_record = [{"id": 1, "texto": "x" * 500, "data_disponibilizacao": "2026-04-01"}]
        _make_zip(zip_path, {"a.json": big_record})

        with pytest.raises(ZipBudgetExceededError, match="uncompressed size"):
            stream_zip_to_ndjson(zip_path, out, "TJSP")


def test_stream_rejects_high_compression_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tiny compressed member that inflates enormously is a decompression bomb shape."""
    monkeypatch.setattr(zip_processor, "MAX_COMPRESSION_RATIO", 5)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        # Highly repetitive content compresses far better than ratio 5x under DEFLATE.
        payload = json.dumps([{"id": 1, "texto": "a" * 200_000}]).encode()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("a.json", payload)

        with pytest.raises(ZipBudgetExceededError, match="compression ratio"):
            stream_zip_to_ndjson(zip_path, out, "TJSP")


def test_stream_rejects_path_traversal_member_name() -> None:
    """A member name escaping the archive root must fail closed, not be silently skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../etc/evil.json", json.dumps([{"id": 1}]))

        with pytest.raises(ZipBudgetExceededError, match="unsafe member name"):
            stream_zip_to_ndjson(zip_path, out, "TJSP")


def test_stream_accepts_normal_zip_unaffected_by_budgets() -> None:
    """The default budgets must not reject a realistic small DJEN-shaped ZIP."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {"a.json": [{"id": 1, "data_disponibilizacao": "2026-04-01"}]},
        )

        count = stream_zip_to_ndjson(zip_path, out, "TJSP")

        assert count == 1


def test_download_zip_enforces_byte_budget() -> None:
    """A response that keeps streaming past the declared budget must abort, not fill disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "out.zip"

        with respx.mock(assert_all_called=True) as router:
            router.get("https://archive.org/download/item/big.zip").mock(
                return_value=httpx.Response(200, content=b"x" * 1_000)
            )

            with pytest.raises(DownloadTooLargeError):
                download_zip("item", "big.zip", output_path, max_bytes=100)

        assert not output_path.exists()


def test_download_zip_allows_response_within_budget() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "out.zip"

        with respx.mock(assert_all_called=True) as router:
            router.get("https://archive.org/download/item/small.zip").mock(
                return_value=httpx.Response(200, content=b"x" * 50)
            )

            ok = download_zip("item", "small.zip", output_path, max_bytes=100)

        assert ok is True
        assert output_path.read_bytes() == b"x" * 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
