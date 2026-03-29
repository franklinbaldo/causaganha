from __future__ import annotations

import base64


"""BDD steps for the collect and upload feature."""


import hashlib
from typing import TYPE_CHECKING, Any

from pytest_bdd import given, parsers, scenario, then, when

from tests.djen_backup.conftest import FAKE_AUTH


if TYPE_CHECKING:
    import httpx
    import respx

# ── Scenarios ────────────────────────────────────────────────────────


@scenario("collect.feature", "Successfully download and upload a ZIP")
def test_upload_zip() -> None:
    pass


@scenario("collect.feature", "Upload includes Content-MD5 header")
def test_upload_md5() -> None:
    pass


@scenario("collect.feature", "Idempotent — already uploaded item is skipped")
def test_idempotent() -> None:
    pass


@scenario("collect.feature", "Respects concurrency limit of 10 requests")
def test_concurrency_limit() -> None:
    pass


# ── Helpers ──────────────────────────────────────────────────────────


def _make_zip(size: int) -> bytes:
    return b"\x00" * size


# ── Given ────────────────────────────────────────────────────────────


@given(
    parsers.parse('DJEN proxy returns a caderno URL for "{tribunal}" on "{date_str}"'),
    target_fixture="item_context",
)
def given_djen_caderno(
    mock_api: respx.MockRouter,
    tribunal: str,
    date_str: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    download_url = f"https://djen-proxy.test/download/{tribunal}-{date_str}.zip"
    caderno_url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{date_str}/D"
    mock_api.get(caderno_url).respond(200, json={"url": download_url})
    context["tribunal"] = tribunal
    context["date_str"] = date_str
    context["download_url"] = download_url
    return context


@given(
    parsers.parse("the caderno URL serves a valid ZIP of {size:d} bytes"),
)
def given_zip_download(
    mock_api: respx.MockRouter,
    size: int,
    context: dict[str, Any],
) -> None:
    content = _make_zip(size)
    context["zip_content"] = content
    mock_api.get(context["download_url"]).respond(200, content=content)


# ── Then ─────────────────────────────────────────────────────────────


@then(
    parsers.parse('the ZIP should be uploaded to Internet Archive as "{filename}"'),
)
def then_uploaded(context: dict[str, Any], filename: str) -> None:
    ia_requests: list[httpx.Request] = context["ia_requests"]
    urls = [str(r.url) for r in ia_requests]
    matching = [u for u in urls if filename in u]
    assert matching, f"Expected upload of {filename}, got URLs: {urls}"


@then("the upload should include correct IA S3 headers")
def then_ia_headers(context: dict[str, Any]) -> None:
    ia_requests: list[httpx.Request] = context["ia_requests"]
    assert ia_requests, "No IA upload requests captured"
    req = ia_requests[0]
    assert req.headers.get("authorization") == FAKE_AUTH
    assert "x-archive-meta-collection" in req.headers
    assert "x-archive-meta-title" in req.headers
    assert req.headers["x-archive-auto-make-bucket"] == "1"
    assert req.headers["x-archive-queue-derive"] == "0"


@then("the upload Content-MD5 should match the file's MD5 hash")
def then_md5_matches(context: dict[str, Any]) -> None:

    ia_requests: list[httpx.Request] = context["ia_requests"]
    assert ia_requests
    req = ia_requests[0]
    actual_md5 = req.headers.get("content-md5")
    digest = hashlib.md5(context["zip_content"], usedforsecurity=False).digest()
    expected_md5 = base64.b64encode(digest).decode("ascii")
    assert actual_md5 == expected_md5, f"MD5 mismatch: {actual_md5} != {expected_md5}"


import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import httpx

from djen_backup.runner import RunConfig, WorkItem, run


@given(parsers.parse('a batch of {count:d} tribunals on "{date_str}"'))
def given_batch_of_tribunals(count: int, date_str: str, context: dict[str, Any]) -> None:
    context["tribunal_count"] = count
    context["date_str"] = date_str
    context["tribunals"] = [f"TRT{i}" for i in range(1, count + 1)]


@when("I process the batch concurrently")
def when_process_batch_concurrently(context: dict[str, Any], mock_api: respx.MockRouter) -> None:
    date_str = context["date_str"]
    tribunals = context["tribunals"]

    # Mock the discovery and list to return our exact tribunals
    mock_api.get("https://djen-proxy.test/api/v1/tribunais").respond(
        200, json={"tribunais": tribunals}
    )
    mock_api.get("https://djen-proxy.test/api/v1/comunicacao/tribunal").respond(200, json=[])
    mock_api.get(f"https://archive.org/metadata/backup-djen-{date_str}").respond(
        200, json={"files": []}
    )

    # Track concurrency
    context["active_requests"] = 0
    context["max_active_requests"] = 0

    async def mock_caderno_route(request):
        context["active_requests"] += 1
        context["max_active_requests"] = max(
            context["max_active_requests"], context["active_requests"]
        )

        await asyncio.sleep(0.01)  # Small delay to allow concurrency

        context["active_requests"] -= 1
        return httpx.Response(200, json={"url": "https://djen-proxy.test/download/mock.zip"})

    # Note: discovering_gaps checks for missing data by calling fetch_ia_existing which we mock,
    # but the logic queries the actual full list of tribunals when force_recheck=False and IA exists isn't there.
    # We must mock the route for ANY tribunal since get_tribunal_list might return 96 of them
    import re
    caderno_pattern = re.compile(r"https://djen-proxy\.test/api/v1/caderno/[A-Za-z0-9-]+/" + date_str + r"/D")
    mock_api.get(url=caderno_pattern).mock(side_effect=mock_caderno_route)
    mock_api.get("https://djen-proxy.test/download/mock.zip").respond(200, content=b"mockzip")

    # Mock IA upload
    mock_api.put(url__startswith="https://s3.us.archive.org/").respond(200)

    d = date.fromisoformat(date_str)
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

    asyncio.run(run(config))


@then(parsers.parse("no more than {limit:d} simultaneous requests should be made"))
def then_verify_concurrency(limit: int, context: dict[str, Any]) -> None:
    assert context["max_active_requests"] <= limit, (
        f"Expected max {limit} requests, got {context['max_active_requests']}"
    )
    assert context["max_active_requests"] > 1, (
        f"Expected concurrent requests, but max was {context['max_active_requests']}"
    )
