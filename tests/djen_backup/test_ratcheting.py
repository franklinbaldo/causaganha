import asyncio
from datetime import date, timedelta
import httpx
import respx
import pytest
from pytest_bdd import given, parsers, scenario, then, when
import time
from djen_backup.backfill import (
    BackfillState,
    BackfillConfig,
    BackfillSummary,
    TribunalProgress,
    backfill_tribunal,
    CircuitBreaker,
)
from djen_backup.state import State
from typing import Any

# ── Scenarios ────────────────────────────────────────────────────────

@scenario("../ratcheting.feature", "Stopped tribunal stops at previous boundary if no new data found")
def test_stopped_tribunal_stops_at_boundary():
    pass

@scenario("../ratcheting.feature", "Stopped tribunal resumes scanning if data is found")
def test_stopped_tribunal_resumes_scanning():
    pass

# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def context():
    return {}

# ── Steps ────────────────────────────────────────────────────────────

@given(parsers.parse('a tribunal "{tribunal}" stopped at "{stop_date}" with 60 empties'))
def given_stopped_tribunal(tribunal: str, stop_date: str, context: dict[str, Any]):
    bstate = BackfillState()
    prog = TribunalProgress(
        cursor_date=date.fromisoformat(stop_date),
        empty_streak=60,
        stopped=True
    )
    bstate._tribunals[tribunal] = prog
    context["tribunal"] = tribunal
    context["bstate"] = bstate
    context["stop_date"] = date.fromisoformat(stop_date)

@when(parsers.parse('backfill runs starting from "{start_date}"'))
def when_backfill_runs(start_date: str, context: dict[str, Any]):
    context["start_date"] = date.fromisoformat(start_date)
    tribunal = context["tribunal"]
    bstate = context["bstate"]

    # 2. Simulate run_backfill logic: ensure cursor is at least today
    # ensure_cursor_at_least is called
    async def _ensure():
        await bstate.ensure_cursor_at_least(tribunal, date.fromisoformat(start_date))
    asyncio.run(_ensure())

    prog = bstate._tribunals[tribunal]
    context["prog"] = prog

@when(parsers.parse('no data is found between "{start_date}" and "{stop_date}"'))
def when_no_data_found(start_date: str, stop_date: str, context: dict[str, Any], mock_api: respx.MockRouter):
    tribunal = context["tribunal"]

    # Mock DJEN to always return 404
    mock_api.get(url__regex=r"https://djen-proxy\.test/api/v1/caderno/.*").respond(404)
    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(200)

    _run_backfill(context, mock_api)

@when(parsers.parse('data is found at "{hit_date}"'))
def when_data_found(hit_date: str, context: dict[str, Any], mock_api: respx.MockRouter):
    tribunal = context["tribunal"]
    hit_d = date.fromisoformat(hit_date)

    # Mock hit date FIRST (so it takes precedence if using regex order)
    mock_api.get(url__regex=rf"https://djen-proxy\.test/api/v1/caderno/{tribunal}/{hit_d.isoformat()}/D").respond(200, json={"url": "http://djen-proxy.test/zip"})
    mock_api.get("http://djen-proxy.test/zip").respond(200, content=b"zipcontent")

    # Mock other dates as 404
    mock_api.get(url__regex=r"https://djen-proxy\.test/api/v1/caderno/.*").respond(404)
    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(200)

    _run_backfill(context, mock_api)

def _run_backfill(context: dict[str, Any], mock_api: respx.MockRouter):
    tribunal = context["tribunal"]
    bstate = context["bstate"]
    start_date = context["start_date"]

    config = BackfillConfig(
        start_date=start_date,
        lower_bound=None,
        tribunal=tribunal,
        deadline_minutes=10,
        max_items=200, # enough to pass the boundary
        workers=1,
        backfill_state_file=None,
        state_file=None,
        djen_proxy_url="https://djen-proxy.test",
        ia_auth="test",
        dry_run=False
    )

    ia_state = State()
    summary = BackfillSummary()
    breaker = CircuitBreaker()
    deadline = time.monotonic() + 600

    async def _run():
        async with httpx.AsyncClient() as client:
            await backfill_tribunal(
                client,
                breaker,
                tribunal,
                config,
                bstate,
                ia_state,
                deadline,
                summary,
            )
    asyncio.run(_run())

@then(parsers.parse('the tribunal cursor should remain at "{expected_date}"'))
def then_cursor_remains(expected_date: str, context: dict[str, Any]):
    prog = context["prog"]
    expected = date.fromisoformat(expected_date)
    assert prog.cursor_date == expected

@then("the tribunal should be stopped")
def then_tribunal_stopped(context: dict[str, Any]):
    prog = context["prog"]
    assert prog.stopped is True
    assert prog.stop_boundary is None # Cleared

@then(parsers.parse('the tribunal cursor should be older than "{expected_date}"'))
def then_cursor_older(expected_date: str, context: dict[str, Any]):
    prog = context["prog"]
    expected = date.fromisoformat(expected_date)
    assert prog.cursor_date < expected
    assert prog.stop_boundary is None
