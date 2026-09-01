"""HTTP transport must expose a minimal, source-free health/version check.

Follow-up to #964 (next slice of #950): a deployed instance needs an
observable version/commit and a proof that the MCP catalog is up and
responding, without turning every upstream source into a boot requirement.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import causaganha_mcp.http_server as http_entry
from causaganha_mcp import __version__
from causaganha_mcp.server import build_server


@pytest.fixture
def client() -> TestClient:
    app = http_entry.mcp.http_app(path="/mcp")
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_reports_ok_status(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_health_endpoint_reports_installed_version(
    client: TestClient,
) -> None:
    response = client.get("/health")

    assert response.json()["version"] == __version__


async def test_health_endpoint_tool_count_matches_canonical_catalog(
    client: TestClient,
) -> None:
    expected_tools = await build_server().list_tools()

    response = client.get("/health")

    assert response.json()["tools"] == len(expected_tools)


def test_health_endpoint_defaults_commit_to_unknown(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.delenv("CAUSAGANHA_MCP_COMMIT", raising=False)

    response = client.get("/health")

    assert response.json()["commit"] == "unknown"


def test_health_endpoint_reports_commit_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("CAUSAGANHA_MCP_COMMIT", "abc1234")

    response = client.get("/health")

    assert response.json()["commit"] == "abc1234"


def test_health_endpoint_does_not_require_post(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
