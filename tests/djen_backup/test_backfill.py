from __future__ import annotations
from dataclasses import replace
import time

"""BDD steps for the backfill feature."""


import asyncio
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import httpx
from pytest_bdd import given, parsers, scenario, then, when

from djen_backup.archive import CircuitBreaker
from djen_backup.backfill import (
    BackfillConfig,
    BackfillState,
    BackfillSummary,
    TribunalProgress,
    backfill_process_date,
    backfill_tribunal,
)
from djen_backup.state import ItemStatus, State


if TYPE_CHECKING:
    import respx

FAKE_AUTH = "LOW test-access:test-secret"
BASE_DATE = date(2024, 6, 1)

# ── Scenarios ────────────────────────────────────────────────────────


@scenario("backfill.feature", "60 consecutive empty dates stop tribunal")
def test_60_empties_stop() -> None:
    pass


@scenario("backfill.feature", "Hit before 60 resets streak")
def test_hit_resets_streak() -> None:
    pass


@scenario("backfill.feature", "Errors do not count as empty")
def test_errors_not_counted() -> None:
    pass


@scenario("backfill.feature", "Stopped tribunal is skipped on next run")
def test_stopped_skipped() -> None:
    pass


@scenario("backfill.feature", "Manual reset re-enables tribunal")
def test_manual_reset() -> None:
    pass


@scenario("backfill.feature", "Lower bound stops scanning")
def test_lower_bound() -> None:
    pass


@scenario("backfill.feature", "No lower bound — stop rule halts scanning")
def test_no_lower_bound() -> None:
    pass


@scenario("backfill.feature", "Already-uploaded item on IA counts as hit")
def test_ia_uploaded_counts_as_hit() -> None:
    pass


# ── Helpers ──────────────────────────────────────────────────────────


def _make_bstate(tribunal: str, streak: int, *, stopped: bool = False) -> BackfillState:
    bstate = BackfillState()
    cursor = BASE_DATE - timedelta(days=streak)
    prog = TribunalProgress(
        cursor_date=cursor,
        empty_streak=streak,
        stopped=stopped,
    )
    bstate._tribunals[tribunal] = prog
    return bstate


_DEFAULT_LOWER = date(2020, 1, 1)
_SENTINEL: date = _DEFAULT_LOWER  # only used as a type-compatible default


def _make_config(
    *,
    lower_bound: date | None = _SENTINEL,
    max_items: int = 0,
    dry_run: bool = False,
) -> BackfillConfig:
    resolved = lower_bound if lower_bound is not _SENTINEL else _DEFAULT_LOWER
    return BackfillConfig(
        start_date=BASE_DATE,
        lower_bound=resolved,
        tribunal=None,
        deadline_minutes=45,
        max_items=max_items,
        workers=1,
        backfill_state_file=None,
        state_file=None,
        djen_proxy_url="https://djen-proxy.test",
        ia_auth=FAKE_AUTH,
        dry_run=dry_run,
    )


# ── Given ────────────────────────────────────────────────────────────


@given(
    parsers.parse('a tribunal "{tribunal}" with {streak:d} consecutive empties'),
    target_fixture="bf_context",
)
def given_tribunal_with_streak(
    tribunal: str,
    streak: int,
    context: dict[str, Any],
) -> dict[str, Any]:
    context["tribunal"] = tribunal
    context["bstate"] = _make_bstate(tribunal, streak)
    context["ia_state"] = State()
    context["config"] = _make_config()
    return context


@given(
    parsers.parse('a tribunal "{tribunal}" that is already stopped'),
    target_fixture="bf_context",
)
def given_stopped_tribunal(
    tribunal: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    context["tribunal"] = tribunal
    context["bstate"] = _make_bstate(tribunal, 60, stopped=True)
    context["ia_state"] = State()
    context["config"] = _make_config()
    return context


@given(
    parsers.parse('a tribunal "{tribunal}" at the lower bound date'),
    target_fixture="bf_context",
)
def given_tribunal_at_lower_bound(
    tribunal: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    # Cursor is already past the lower bound — nothing to scan
    lb = date(2024, 1, 1)
    bstate = BackfillState()
    bstate._tribunals[tribunal] = TribunalProgress(cursor_date=lb - timedelta(days=1))
    context["tribunal"] = tribunal
    context["bstate"] = bstate
    context["ia_state"] = State()
    context["config"] = _make_config(lower_bound=lb)
    return context


@given("DJEN proxy returns 404 for the next date")
def given_djen_404_next(
    mock_api: respx.MockRouter,
    context: dict[str, Any],
) -> None:
    tribunal = context["tribunal"]
    bstate: BackfillState = context["bstate"]
    cursor = bstate._tribunals[tribunal].cursor_date
    caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{cursor.isoformat()}/D"
    mock_api.get(caderno_url).respond(404)


@given("DJEN proxy returns a valid ZIP for the next date")
def given_djen_zip_next(
    mock_api: respx.MockRouter,
    context: dict[str, Any],
) -> None:
    tribunal = context["tribunal"]
    bstate: BackfillState = context["bstate"]
    cursor = bstate._tribunals[tribunal].cursor_date
    caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{cursor.isoformat()}/D"
    download_url = f"https://djen-proxy.test/download/{tribunal}.zip"
    mock_api.get(caderno_url).respond(200, json={"url": download_url})
    mock_api.get(download_url).respond(200, content=b"\x00" * 256)


@given("DJEN proxy returns a server error for the next date")
def given_djen_500_next(
    mock_api: respx.MockRouter,
    context: dict[str, Any],
) -> None:
    tribunal = context["tribunal"]
    bstate: BackfillState = context["bstate"]
    cursor = bstate._tribunals[tribunal].cursor_date
    caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{cursor.isoformat()}/D"
    mock_api.get(caderno_url).respond(500)


@given(
    parsers.parse('IA state marks the next date as "{status_str}"'),
)
def given_ia_state_marks(
    context: dict[str, Any],
    status_str: str,
) -> None:
    tribunal = context["tribunal"]
    bstate: BackfillState = context["bstate"]
    ia_state: State = context["ia_state"]
    cursor = bstate._tribunals[tribunal].cursor_date
    status = ItemStatus.UPLOADED if status_str == "uploaded" else ItemStatus.ABSENT

    async def _mark() -> None:
        await ia_state.mark(cursor, tribunal, status)

    asyncio.run(_mark())


# ── When ─────────────────────────────────────────────────────────────


@when(
    parsers.parse('I backfill "{tribunal}" for {n:d} date'),
    target_fixture="bf_result",
)
@when(
    parsers.parse('I backfill "{tribunal}" for {n:d} dates'),
    target_fixture="bf_result",
)
def when_backfill(
    tribunal: str,
    n: int,
    mock_api: respx.MockRouter,
    context: dict[str, Any],
) -> dict[str, Any]:
    bstate: BackfillState = context["bstate"]
    ia_state: State = context["ia_state"]
    config: BackfillConfig = context["config"]

    # Limit to requested number of dates

    config = replace(config, max_items=n)

    # IA uploads accepted
    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(200)

    summary = BackfillSummary()

    async def _run() -> None:
        breaker = CircuitBreaker(threshold=5)

        deadline = time.monotonic() + 300
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
    context["summary"] = summary
    return context


@when(
    parsers.parse('I backfill "{tribunal}" for {n:d} date with no lower bound'),
    target_fixture="bf_result",
)
@when(
    parsers.parse('I backfill "{tribunal}" for {n:d} dates with no lower bound'),
    target_fixture="bf_result",
)
def when_backfill_no_lower(
    tribunal: str,
    n: int,
    mock_api: respx.MockRouter,
    context: dict[str, Any],
) -> dict[str, Any]:
    bstate: BackfillState = context["bstate"]
    ia_state: State = context["ia_state"]
    config = _make_config(lower_bound=None, max_items=n)

    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(200)

    summary = BackfillSummary()

    async def _run() -> None:
        breaker = CircuitBreaker(threshold=5)

        deadline = time.monotonic() + 300
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
    context["summary"] = summary
    return context


@when(
    parsers.parse('I reset "{tribunal}"'),
    target_fixture="bf_result",
)
def when_reset(
    tribunal: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    bstate: BackfillState = context["bstate"]

    async def _run() -> None:
        await bstate.reset_tribunal(tribunal)

    asyncio.run(_run())
    return context


# ── Then ─────────────────────────────────────────────────────────────


@then(
    parsers.parse('"{tribunal}" should be stopped'),
)
def then_stopped(tribunal: str, context: dict[str, Any]) -> None:
    bstate: BackfillState = context["bstate"]
    prog = bstate._tribunals[tribunal]
    assert prog.stopped, f"{tribunal} expected stopped but is running (streak={prog.empty_streak})"


@then(
    parsers.parse('"{tribunal}" should not be stopped'),
)
def then_not_stopped(tribunal: str, context: dict[str, Any]) -> None:
    bstate: BackfillState = context["bstate"]
    prog = bstate._tribunals[tribunal]
    assert not prog.stopped, f"{tribunal} expected running but is stopped"


@then(
    parsers.parse('"{tribunal}" should still be stopped'),
)
def then_still_stopped(tribunal: str, context: dict[str, Any]) -> None:
    bstate: BackfillState = context["bstate"]
    prog = bstate._tribunals[tribunal]
    assert prog.stopped, f"{tribunal} expected still stopped"


@then(
    parsers.parse("the empty streak should be {n:d}"),
)
def then_streak(n: int, context: dict[str, Any]) -> None:
    tribunal = context["tribunal"]
    bstate: BackfillState = context["bstate"]
    prog = bstate._tribunals[tribunal]
    assert prog.empty_streak == n, f"Expected streak {n}, got {prog.empty_streak}"


@then(
    parsers.parse("the backfill summary should show {n:d} skipped stopped"),
)
def then_skipped_stopped(n: int, context: dict[str, Any]) -> None:
    summary: BackfillSummary = context["summary"]
    assert summary.tribunals_skipped_stopped == n, (
        f"Expected {n} skipped stopped, got {summary.tribunals_skipped_stopped}"
    )


@then(
    parsers.parse("the backfill summary should show {n:d} dates processed"),
)
def then_dates_processed(n: int, context: dict[str, Any]) -> None:
    summary: BackfillSummary = context["summary"]
    total = summary.hits + summary.empties + summary.errors
    assert total == n, f"Expected {n} dates processed, got {total}"


def test_backfill_process_date_returns_spam_on_ia_spam_rejection(
    mock_api: respx.MockRouter,
) -> None:
    tribunal = "tjsp"
    bstate = _make_bstate(tribunal, 0)
    ia_state = State()
    config = _make_config(max_items=1)
    summary = BackfillSummary()
    cursor = bstate._tribunals[tribunal].cursor_date

    caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{cursor.isoformat()}/D"
    download_url = f"https://djen-proxy.test/download/{tribunal}.zip"
    mock_api.get(caderno_url).respond(200, json={"url": download_url})
    mock_api.get(download_url).respond(200, content=b"\x00" * 256)
    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(
        400,
        content=b"Item appears to be spam",
    )

    async def _run() -> str:
        breaker = CircuitBreaker(threshold=5)
        async with httpx.AsyncClient() as client:
            return await backfill_process_date(
                client,
                breaker,
                tribunal,
                cursor,
                config,
                bstate,
                ia_state,
                summary,
            )

    result = asyncio.run(_run())
    assert result == "spam"
    assert summary.errors == 1
    assert summary.ia_errors == 0
    assert bstate._tribunals[tribunal].cursor_date == cursor


def test_backfill_tribunal_advances_cursor_on_spam_rejection(
    mock_api: respx.MockRouter,
) -> None:
    tribunal = "tjsp"
    bstate = _make_bstate(tribunal, 0)
    ia_state = State()
    config = _make_config(max_items=1)
    summary = BackfillSummary()
    cursor = bstate._tribunals[tribunal].cursor_date

    caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{cursor.isoformat()}/D"
    download_url = f"https://djen-proxy.test/download/{tribunal}.zip"
    mock_api.get(caderno_url).respond(200, json={"url": download_url})
    mock_api.get(download_url).respond(200, content=b"\x00" * 256)
    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(
        400,
        content=b"Item appears to be spam",
    )

    async def _run() -> None:
        breaker = CircuitBreaker(threshold=5)

        deadline = time.monotonic() + 300
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
    assert bstate._tribunals[tribunal].cursor_date == cursor - timedelta(days=1)
    assert summary.errors == 1
    assert summary.ia_errors == 0
