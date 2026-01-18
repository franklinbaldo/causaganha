"""Integration tests for the archive pipeline."""

from unittest.mock import AsyncMock, patch

import pytest
from ibis.backends.duckdb import Backend

from causaganha.v2.pipeline.archive import archive_documents
from causaganha.v2.api.client import Intimation
from causaganha.v2.storage.queries import store_intimations


@pytest.fixture
def sample_intimations() -> list[Intimation]:
    """Provide sample intimations."""
    return [
        Intimation(
            id=101,
            numero_processo="101-89.2024.8.22.0001",
            siglaTribunal="TJRO",
            data_disponibilizacao="2024-01-01",
            link="http://example.com/101.pdf",
            texto="Intimation 101",
        ),
        Intimation(
            id=102,
            numero_processo="102-89.2024.8.22.0001",
            siglaTribunal="TJRO",
            data_disponibilizacao="2024-01-02",
            link="http://example.com/102.pdf",
            texto="Intimation 102",
        ),
    ]


@pytest.mark.asyncio
async def test_archive_pipeline_integration(
    db_connection: Backend,
    sample_intimations: list[Intimation],
) -> None:
    """Test the archive pipeline with real DB and mocked Archive Service."""

    # 1. Store intimations in DB
    store_intimations(db_connection, sample_intimations)

    # Verify they are unarchived
    t = db_connection.table("intimations")
    res = t.execute()
    assert len(res) == 2
    # Ensure ia_url column exists and is null (or check if it's None)
    # Ibis/DuckDB might return NaN for float/double nulls or None for strings.
    # The schema defines ia_url as string (TEXT).
    assert res["ia_url"].isna().all()

    # 2. Run archive pipeline with mocks
    with patch("causaganha.v2.pipeline.archive.PreservationService") as mock_pres_cls:
        mock_service = mock_pres_cls.return_value

        # Mock preserve_document to return a fake URL based on ID
        async def _preserve(url, item_id, metadata, dry_run):
            # item_id is like "causaganha-tjro-101"
            _id = item_id.split("-")[-1]
            return f"https://archive.org/{_id}"

        mock_service.preserve_document = AsyncMock(side_effect=_preserve)

        # We also need to mock DocumentService and ArchiveService passed to the function
        mock_doc = AsyncMock()
        mock_archive = AsyncMock()
        mock_archive.generate_metadata.return_value = {"creator": "CausaGanha"}

        result = await archive_documents(
            mock_doc,
            mock_archive,
            limit=10
        )

        assert result["status"] == "success"
        assert result["archived"] == 2

        # 3. Verify DB updates
        res_after = t.execute()

        row_101 = res_after[res_after["id"] == 101].iloc[0]
        row_102 = res_after[res_after["id"] == 102].iloc[0]

        assert row_101["ia_url"] == "https://archive.org/101"
        assert row_102["ia_url"] == "https://archive.org/102"
