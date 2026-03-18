"""BDD steps for the absent marking feature."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pytest_bdd import given, parsers, scenario, then

if TYPE_CHECKING:
    import httpx
    import respx


# ── Scenarios ────────────────────────────────────────────────────────


@scenario("../absent_marking.feature", "Mark absent when DJEN returns 404")
def test_absent_404() -> None:
    pass


@scenario("../absent_marking.feature", "Mark absent when DJEN returns empty URL")
def test_absent_empty() -> None:
    pass


# ── Given ────────────────────────────────────────────────────────────


@given(
    parsers.parse('DJEN proxy returns 404 for "{tribunal}" on "{date_str}"'),
    target_fixture="item_context",
)
def given_djen_404(
    mock_api: respx.MockRouter,
    tribunal: str,
    date_str: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{date_str}/D"
    mock_api.get(url).respond(404)
    context["tribunal"] = tribunal
    context["date_str"] = date_str
    return context


@given(
    parsers.parse('DJEN proxy returns an empty URL for "{tribunal}" on "{date_str}"'),
    target_fixture="item_context",
)
def given_djen_empty_url(
    mock_api: respx.MockRouter,
    tribunal: str,
    date_str: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    url = f"https://djen-proxy.test/api/v1/caderno/{tribunal}/{date_str}/D"
    mock_api.get(url).respond(200, json={"url": ""})
    context["tribunal"] = tribunal
    context["date_str"] = date_str
    return context


# ── Then ─────────────────────────────────────────────────────────────


@then(
    parsers.parse('an absent marker should be uploaded as "{filename}"'),
)
def then_absent_uploaded(context: dict[str, Any], filename: str) -> None:
    ia_requests: list[httpx.Request] = context["ia_requests"]
    urls = [str(r.url) for r in ia_requests]
    matching = [u for u in urls if filename in u]
    assert matching, f"Expected absent marker upload for {filename}, got URLs: {urls}"


@then(
    parsers.parse("the absent marker should contain JSON with status_code {code:d}"),
)
def then_absent_json(context: dict[str, Any], code: int) -> None:
    ia_requests: list[httpx.Request] = context["ia_requests"]
    assert ia_requests
    body = json.loads(ia_requests[0].content)
    assert body["status_code"] == code
    assert "checked_at" in body
