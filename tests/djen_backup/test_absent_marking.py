"""BDD steps for the absent marking feature."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pytest_bdd import given, parsers, scenario


if TYPE_CHECKING:
    import respx


# ── Scenarios ────────────────────────────────────────────────────────


@scenario("absent_marking.feature", "Mark absent when DJEN returns 404")
def test_absent_404() -> None:
    pass


@scenario("absent_marking.feature", "Mark absent when DJEN returns empty URL")
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

# (Removed then_absent_uploaded and then_absent_json as they are no longer in the feature)
