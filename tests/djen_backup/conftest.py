from __future__ import annotations

from djen_backup.runner import discover_gaps


"""Shared fixtures and step definitions for BDD step implementations."""


import asyncio
import time
from datetime import date
from typing import Any

import httpx
import pytest
import respx
from pytest_bdd import given, parsers, then, when

from djen_backup.archive import CircuitBreaker
from djen_backup.runner import RunConfig, Summary, WorkItem, process_item
from djen_backup.state import State


FAKE_AUTH = "LOW test-access:test-secret"


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_api() -> respx.MockRouter:
    """A ``respx`` mock router activated for the test."""
    with respx.mock(assert_all_called=False) as router:
        # Default: IA HEAD check returns 404 (item not on IA yet)
        router.head(url__startswith="https://archive.org/download/").respond(404)
        yield router


@pytest.fixture
def state() -> State:
    return State()


@pytest.fixture
def circuit_breaker() -> CircuitBreaker:
    return CircuitBreaker(threshold=5, recovery_timeout=60.0)


@pytest.fixture
def context() -> dict[str, Any]:
    """A mutable bag for sharing data across Given/When/Then steps."""
    return {}


def parse_table(datatable: list[list[str]]) -> list[dict[str, str]]:
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    headers = datatable[0]
    return [dict(zip(headers, row, strict=False)) for row in datatable[1:]]


# ── Shared Given steps ──────────────────────────────────────────────


@given("Internet Archive accepts uploads")
def given_ia_accepts(mock_api: respx.MockRouter, context: dict[str, Any]) -> None:
    context["ia_requests"] = []

    def _capture(request: httpx.Request) -> httpx.Response:
        context["ia_requests"].append(request)
        return httpx.Response(200)

    mock_api.put(url__startswith="https://s3.us.archive.org/").mock(side_effect=_capture)


@given(
    parsers.parse('Internet Archive has files for "{date_str}":'),
    target_fixture="ia_date_str",
)
def given_ia_files(
    mock_api: respx.MockRouter,
    date_str: str,
    datatable: list[list[str]],
) -> str:
    rows = parse_table(datatable)
    filenames = [row["filename"] for row in rows]
    payload = {"files": [{"name": fn} for fn in filenames]}
    mock_api.get(f"https://archive.org/metadata/backup-djen-{date_str}").respond(200, json=payload)
    return date_str


@given(
    "the tribunal list is:",
    target_fixture="tribunal_list",
)
def given_tribunal_list(datatable: list[list[str]]) -> list[str]:
    rows = parse_table(datatable)
    return [row["tribunal"] for row in rows]


# ── Shared When steps ───────────────────────────────────────────────


@when(
    parsers.parse('I process the item "{tribunal}" on "{date_str}"'),
    target_fixture="process_result",
)
def when_process_item(
    state: State,
    mock_api: respx.MockRouter,
    tribunal: str,
    date_str: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    d = date.fromisoformat(date_str)
    item = WorkItem(date=d, tribunal=tribunal)
    config = RunConfig(
        start_date=d,
        end_date=d,
        tribunal=tribunal,
        deadline_minutes=45,
        max_items=0,
        workers=1,
        state_file=None,
        djen_proxy_url="https://djen-proxy.test",
        ia_auth=FAKE_AUTH,
        dry_run=False,
        force_recheck=False,
    )

    async def _run() -> None:
        summary = Summary(total=1)
        breaker = CircuitBreaker(threshold=5)
        deadline = time.monotonic() + 300
        async with httpx.AsyncClient() as client:
            await process_item(client, breaker, item, state, config, deadline, summary)
        context["summary"] = summary

    asyncio.run(_run())
    context["state"] = state
    context["date"] = d
    return context


@when(
    parsers.parse('I detect gaps for "{date_str}"'),
    target_fixture="gaps",
)
def when_detect_gaps(
    state: State,
    tribunal_list: list[str],
    date_str: str,
) -> list[WorkItem]:

    d = date.fromisoformat(date_str)

    async def _run() -> list[WorkItem]:
        async with httpx.AsyncClient() as client:
            return await discover_gaps(client, state, tribunal_list, d, d, force_recheck=False)

    return asyncio.run(_run())


# ── Shared Then steps ───────────────────────────────────────────────


@then(
    parsers.parse('the state should mark "{tribunal}" on "{date_str}" as "{status}"'),
)
def then_state_mark(state: State, tribunal: str, date_str: str, status: str) -> None:
    d = date.fromisoformat(date_str)
    assert state.is_done(d, tribunal), f"{tribunal} on {date_str} not marked in state"


@then("there should be no gaps")
def then_no_gaps(gaps: list[WorkItem]) -> None:
    assert len(gaps) == 0, f"Expected no gaps, got {gaps}"
