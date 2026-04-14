"""Shared fixtures for consolidate BDD tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def manifest_path(tmp_path: Path) -> Path:
    """Path to a disposable sync-manifest.csv file per test."""
    return tmp_path / "sync-manifest.csv"


def write_manifest(path: Path, rows: list[dict]) -> None:
    """Write rows to a sync-manifest.csv with the expected header."""
    header = "tribunal,date,ia_status,djen_status,djen_raw,updated_at"
    lines = [header]
    for row in rows:
        line = (
            f"{row.get('tribunal', 'TJSP')},"
            f"{row['date']},"
            f"{row.get('ia_status', '')},"
            f"{row.get('djen_status', '')},"
            f"{row.get('djen_raw', '')},"
            f"{row.get('updated_at', '')}"
        )
        lines.append(line)
    path.write_text("\n".join(lines) + "\n")
