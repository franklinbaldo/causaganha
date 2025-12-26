from datetime import date
from pathlib import Path
from unittest import mock
import pytest

from causaganha.services.archive import LocalArchiveService

@pytest.mark.asyncio
async def test_local_archive_organization(tmp_path: Path) -> None:
    """Test that LocalArchiveService organizes files by Tribunal/Year/Month."""
    archive_root = tmp_path / "archive"
    service = LocalArchiveService(archive_root=archive_root)

    file_path = tmp_path / "test.pdf"
    file_path.write_text("dummy content")

    metadata = {
        "subject": ["judicial", "tjro"],  # Tribunal is usually last in subject list in current implementation
        "date": date(2023, 10, 15),
        "title": "TJRO - Processo 12345"
    }

    # We pass item_id but expect it to be used only if metadata is missing or for IA compatibility
    # The requirement is: "Update archive.py to organize files by court (e.g., TJRO/YYYY/MM/...)"
    item_id = "causaganha-tjro-12345"

    saved_path_str = await service.upload_file(file_path, item_id, metadata)
    assert saved_path_str is not None
    saved_path = Path(saved_path_str)

    # Expected path: archive_root / TJRO / 2023 / 10 / test.pdf
    # or archive_root / TJRO / 2023 / 10 / item_id / test.pdf ?
    # The TODO says "TJRO/YYYY/MM/...". It probably implies the file goes there.
    # Let's assume: archive_root / tribunal / year / month / filename

    expected_parent = archive_root / "tjro" / "2023" / "10"

    assert saved_path.parent == expected_parent
    assert saved_path.name == "test.pdf"
    assert saved_path.exists()

@pytest.mark.asyncio
async def test_local_archive_fallback_without_metadata(tmp_path: Path) -> None:
    """Test fallback when metadata is missing."""
    archive_root = tmp_path / "archive"
    service = LocalArchiveService(archive_root=archive_root)

    file_path = tmp_path / "test.pdf"
    file_path.write_text("dummy content")

    item_id = "causaganha-tjro-12345"

    # Should fallback to item_id folder as before
    saved_path_str = await service.upload_file(file_path, item_id, None)
    assert saved_path_str is not None
    saved_path = Path(saved_path_str)

    assert saved_path.parent == archive_root / item_id
    assert saved_path.exists()
