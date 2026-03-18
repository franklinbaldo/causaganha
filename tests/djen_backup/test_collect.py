"""BDD steps for the collect and upload feature."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from pytest_bdd import given, parsers, scenario, then

from .conftest import FAKE_AUTH

if TYPE_CHECKING:
    import httpx
    import respx

# ── Scenarios ────────────────────────────────────────────────────────


@scenario("../collect.feature", "Successfully download and upload a ZIP")
def test_upload_zip() -> None:
    pass


@scenario("../collect.feature", "Upload includes Content-MD5 header")
def test_upload_md5() -> None:
    pass


@scenario("../collect.feature", "Idempotent — already uploaded item is skipped")
def test_idempotent() -> None:
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
    import base64

    ia_requests: list[httpx.Request] = context["ia_requests"]
    assert ia_requests
    req = ia_requests[0]
    actual_md5 = req.headers.get("content-md5")
    digest = hashlib.md5(context["zip_content"], usedforsecurity=False).digest()
    expected_md5 = base64.b64encode(digest).decode("ascii")
    assert actual_md5 == expected_md5, f"MD5 mismatch: {actual_md5} != {expected_md5}"
