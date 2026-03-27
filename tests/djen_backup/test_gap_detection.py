"""BDD steps for gap detection feature."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

from pytest_bdd import given, parsers, scenario, then

from djen_backup.state import ItemStatus, State
from tests.djen_backup.conftest import parse_table


if TYPE_CHECKING:
    import respx

    from djen_backup.runner import WorkItem


@scenario("gap_detection.feature", "Detect missing tribunals for a date")
def test_detect_missing() -> None:
    pass


@scenario("gap_detection.feature", "No gaps when all tribunals are covered")
def test_no_gaps() -> None:
    pass


@scenario("gap_detection.feature", "All tribunals missing when IA item does not exist")
def test_all_missing() -> None:
    pass


@scenario("gap_detection.feature", "State cache skips IA query for fully-covered date")
def test_cache_skip() -> None:
    pass


# ── Given ────────────────────────────────────────────────────────────


@given(
    parsers.parse('Internet Archive has no item for "{date_str}"'),
    target_fixture="ia_date_str",
)
def given_ia_empty(mock_api: respx.MockRouter, date_str: str) -> str:
    mock_api.get(f"https://archive.org/metadata/backup-djen-{date_str}").respond(
        200, json={"files": []}
    )
    return date_str


@given(
    parsers.parse('the state cache marks "{date_str}" as fully covered for:'),
    target_fixture="ia_date_str",
)
def given_state_cache_covered(
    state: State,
    date_str: str,
    datatable: list[list[str]],
) -> str:
    d = date.fromisoformat(date_str)
    rows = parse_table(datatable)

    async def _mark() -> None:
        for row in rows:
            await state.mark(d, row["tribunal"], ItemStatus.UPLOADED)

    asyncio.run(_mark())
    return date_str


# ── Then ─────────────────────────────────────────────────────────────


@then("the gaps should be:")
def then_gaps_are(gaps: list[WorkItem], datatable: list[list[str]]) -> None:
    rows = parse_table(datatable)
    expected = {row["tribunal"] for row in rows}
    actual = {item.tribunal for item in gaps}
    assert actual == expected, f"Expected gaps {expected}, got {actual}"


@then("the Internet Archive should not have been queried")
def then_ia_not_queried(mock_api: respx.MockRouter) -> None:
    for route in mock_api.routes:
        url_pattern = str(route.pattern)
        if "archive.org/metadata" in url_pattern:
            assert not route.called, f"IA metadata was queried: {url_pattern}"
