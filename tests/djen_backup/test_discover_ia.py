"""Unit tests for ``_discover_ia_items``.

Covers happy path (well-formed IA advanced-search response), schema
variants that previously crashed startup, and the manifest-fallback
path on HTTP failure.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from djen_backup.engine import _discover_ia_items
from djen_backup.manifest import SyncManifest


_IA_SEARCH_URL = "https://archive.org/advancedsearch.php"


@pytest.mark.asyncio
async def test_discover_parses_well_formed_response() -> None:
    payload = {
        "response": {
            "docs": [
                {"identifier": "djen-tjsp-2024"},
                {"identifier": "djen-tre-ac-2023"},
                {"identifier": "djen-tjba-2024"},
            ]
        }
    }
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith=_IA_SEARCH_URL).respond(200, json=payload)
        existing = await _discover_ia_items(SyncManifest())

    assert existing == {("TJSP", 2024), ("TRE-AC", 2023), ("TJBA", 2024)}


@pytest.mark.asyncio
async def test_discover_skips_identifiers_without_year_suffix() -> None:
    payload = {
        "response": {
            "docs": [
                {"identifier": "djen-tjsp-2024"},
                {"identifier": "djen-no-year"},  # no trailing digits
                {"identifier": "djen-malformed"},
            ]
        }
    }
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith=_IA_SEARCH_URL).respond(200, json=payload)
        existing = await _discover_ia_items(SyncManifest())

    assert existing == {("TJSP", 2024)}


@pytest.mark.asyncio
async def test_discover_falls_back_to_manifest_on_http_error() -> None:
    m = SyncManifest()
    m.build(["TJSP", "TJBA"], date(2024, 1, 1), date(2024, 1, 5))
    await m.mark_uploaded("TJSP", date(2024, 1, 2))  # not in fallback

    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith=_IA_SEARCH_URL).mock(side_effect=httpx.ConnectError("boom"))
        existing = await _discover_ia_items(m)

    # Fallback returns (tribunal, year) for entries still pending upload —
    # not the already-uploaded TJSP/2024-01-02 (it's filtered out, but
    # other TJSP/2024 entries remain).
    assert ("TJSP", 2024) in existing
    assert ("TJBA", 2024) in existing


@pytest.mark.asyncio
async def test_discover_handles_schema_variant_docs_null() -> None:
    """Regression: response with ``docs: null`` previously raised TypeError."""
    payload = {"response": {"docs": None}}
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 2))

    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith=_IA_SEARCH_URL).respond(200, json=payload)
        existing = await _discover_ia_items(m)

    # Falls back to manifest (TJSP/2024 entries pending).
    assert existing == {("TJSP", 2024)}


@pytest.mark.asyncio
async def test_discover_handles_schema_variant_non_dict_entries() -> None:
    """Regression: docs entries that aren't dicts previously raised AttributeError."""
    payload = {
        "response": {
            "docs": [
                {"identifier": "djen-tjsp-2024"},
                "not-a-dict",  # would have raised AttributeError on .rsplit
            ]
        }
    }
    m = SyncManifest()
    m.build(["TJBA"], date(2024, 1, 1), date(2024, 1, 2))

    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith=_IA_SEARCH_URL).respond(200, json=payload)
        existing = await _discover_ia_items(m)

    # Falls back to manifest because of TypeError/AttributeError.
    assert existing == {("TJBA", 2024)}
