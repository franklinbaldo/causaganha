"""Unit tests for the streaming ZIP → NDJSON extractor."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from causaganha.consolidate.zip_processor import stream_zip_to_ndjson


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
        _make_zip(zip_path, {"a.json": [{"id": 1}, {"id": 2}, {"id": 3}]})

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 3
        lines = out.read_text().splitlines()
        assert len(lines) == 3
        assert json.loads(lines[0]) == {"id": 1}


def test_stream_extracts_items_wrapper() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(zip_path, {"a.json": {"items": [{"id": 1}], "status": "ok"}})

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 1
        assert json.loads(out.read_text().strip()) == {"id": 1}


def test_stream_extracts_single_object() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(zip_path, {"a.json": {"id": 42, "texto": "foo"}})

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 1
        assert json.loads(out.read_text().strip()) == {"id": 42, "texto": "foo"}


def test_stream_skips_non_json_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "readme.txt": "ignore me",
                "data.json": [{"id": 1}],
            },
        )

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 1


def test_stream_handles_malformed_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "broken.json": "{not valid json",
                "good.json": [{"id": 1}],
            },
        )

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 1


def test_stream_handles_bad_zip() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "not_a_zip.zip"
        out = Path(tmpdir) / "out.ndjson"
        zip_path.write_bytes(b"garbage")

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 0


def test_stream_combines_multiple_json_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "x.zip"
        out = Path(tmpdir) / "out.ndjson"
        _make_zip(
            zip_path,
            {
                "a.json": [{"id": 1}],
                "b.json": [{"id": 2}, {"id": 3}],
                "c.json": {"items": [{"id": 4}]},
            },
        )

        count = stream_zip_to_ndjson(zip_path, out)

        assert count == 4
        lines = out.read_text().splitlines()
        ids = sorted(json.loads(line)["id"] for line in lines)
        assert ids == [1, 2, 3, 4]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
