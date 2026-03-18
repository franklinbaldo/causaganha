"""BDD steps for the deadline awareness feature."""

from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import TYPE_CHECKING, Any

import httpx
from pytest_bdd import given, parsers, scenario, then, when

from djen_backup.archive import CircuitBreaker
from djen_backup.runner import RunConfig, Summary, WorkItem, process_item

from .conftest import FAKE_AUTH

if TYPE_CHECKING:
    import respx

    from djen_backup.state import State


# ── Scenarios ────────────────────────────────────────────────────────


@scenario("../deadline.feature", "Skip item when deadline is near")
def test_skip_near_deadline() -> None:
    pass


@scenario("../deadline.feature", "Process all items when time is sufficient")
def test_process_all() -> None:
    pass


# ── Given ────────────────────────────────────────────────────────────


@given(
    parsers.parse("the deadline is {seconds:d} seconds from now"),
    target_fixture="deadline_seconds",
)
def given_deadline(seconds: int) -> int:
    return seconds


@given(
    parsers.parse("there are {n:d} items in the work queue"),
    target_fixture="queue_size",
)
def given_queue_size(n: int) -> int:
    return n


# ── When ─────────────────────────────────────────────────────────────


@when(
    parsers.parse("processing takes {seconds:d} seconds per item"),
    target_fixture="deadline_result",
)
def when_process_with_deadline(
    deadline_seconds: int,
    queue_size: int,
    seconds: int,
    state: State,
    mock_api: respx.MockRouter,
) -> dict[str, Any]:
    d = date(2024, 1, 15)

    # Mock DJEN proxy
    for i in range(queue_size):
        tribunal = f"T{i}"
        caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{d.isoformat()}/D"
        download_url = f"https://djen-proxy.test/download/{tribunal}.zip"
        mock_api.get(caderno_url).respond(200, json={"url": download_url})
        mock_api.get(download_url).respond(200, content=b"\x00" * 100)

    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(200)

    config = RunConfig(
        start_date=d,
        end_date=d,
        tribunal=None,
        deadline_minutes=45,
        max_items=0,
        workers=1,
        state_file=None,
        djen_proxy_url="https://djen-proxy.test",
        ia_auth=FAKE_AUTH,
        dry_run=False,
        force_recheck=False,
    )

    items = [WorkItem(date=d, tribunal=f"T{i}") for i in range(queue_size)]

    async def _run() -> Summary:
        summary = Summary(total=queue_size)
        breaker = CircuitBreaker(threshold=5)
        deadline = time.monotonic() + deadline_seconds

        async with httpx.AsyncClient() as client:
            for item in items:
                if seconds > 0:
                    # Simulate time passing by moving the deadline closer
                    deadline -= seconds
                await process_item(client, breaker, item, state, config, deadline, summary)

        return summary

    summary = asyncio.run(_run())

    return {
        "summary": summary,
        "skipped": summary.skipped_deadline,
    }


# ── Then ─────────────────────────────────────────────────────────────


@then(parsers.parse("at least {n:d} item should be skipped due to deadline"))
def then_at_least_skipped(deadline_result: dict[str, Any], n: int) -> None:
    assert deadline_result["skipped"] >= n, (
        f"Expected at least {n} skipped, got {deadline_result['skipped']}"
    )


@then(parsers.parse("{n:d} items should be skipped due to deadline"))
def then_exact_skipped(deadline_result: dict[str, Any], n: int) -> None:
    assert deadline_result["skipped"] == n, (
        f"Expected {n} skipped, got {deadline_result['skipped']}"
    )
