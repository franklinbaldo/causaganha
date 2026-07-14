"""Tests for common.relay — the RELAY_URL/RELAY_TOKEN httpx transport.

Verifies the transport rewrites the request to the relay URL, moves the
original destination + token into headers, and passes method/body through
untouched — using httpx.MockTransport as the "inner" transport so no real
network call happens.
"""

from __future__ import annotations

import json

import httpx
import pytest

from common.relay import (
    AsyncRelayTransport,
    RelayTransport,
    async_relay_transport_from_env,
    relay_transport_from_env,
)


RELAY_URL = "https://relay-abc.a.run.app/"
RELAY_TOKEN = "s3cr3t-token"  # noqa: S105 — test fixture, not a real credential
ORIGINAL_URL = "https://juris-back.tjro.jus.br/search/varios_parametros/"


def test_relay_transport_rewrites_url_and_headers() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = RelayTransport(RELAY_URL, RELAY_TOKEN, inner=httpx.MockTransport(handler))
    with httpx.Client(transport=transport) as client:
        resp = client.post(
            ORIGINAL_URL,
            json={"tipo": "ACÓRDÃO"},
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200
    assert len(captured) == 1
    sent = captured[0]
    assert str(sent.url) == RELAY_URL
    assert sent.headers["X-Relay-Url"] == ORIGINAL_URL
    assert sent.headers["X-Relay-Token"] == RELAY_TOKEN
    assert sent.headers["Content-Type"] == "application/json"
    assert sent.method == "POST"
    assert json.loads(sent.read()) == {"tipo": "ACÓRDÃO"}


def test_relay_transport_preserves_method_and_body() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, text="ok")

    transport = RelayTransport(RELAY_URL, RELAY_TOKEN, inner=httpx.MockTransport(handler))
    with httpx.Client(transport=transport) as client:
        client.get(ORIGINAL_URL, headers={"Accept": "application/json"})

    sent = captured[0]
    assert sent.method == "GET"
    assert sent.headers["Accept"] == "application/json"
    assert sent.read() == b""


@pytest.mark.asyncio
async def test_async_relay_transport_rewrites_url_and_headers() -> None:
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = AsyncRelayTransport(RELAY_URL, RELAY_TOKEN, inner=httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.post(ORIGINAL_URL, json={"from": 0, "size": 1})

    assert resp.status_code == 200
    sent = captured[0]
    assert str(sent.url) == RELAY_URL
    assert sent.headers["X-Relay-Url"] == ORIGINAL_URL
    assert sent.headers["X-Relay-Token"] == RELAY_TOKEN
    assert sent.method == "POST"


def test_relay_transport_from_env_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RELAY_URL", raising=False)
    monkeypatch.delenv("RELAY_TOKEN", raising=False)
    assert relay_transport_from_env() is None
    assert async_relay_transport_from_env() is None


def test_relay_transport_from_env_builds_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_URL", RELAY_URL)
    monkeypatch.setenv("RELAY_TOKEN", RELAY_TOKEN)
    transport = relay_transport_from_env()
    assert isinstance(transport, RelayTransport)
    async_transport = async_relay_transport_from_env()
    assert isinstance(async_transport, AsyncRelayTransport)


def test_relay_transport_from_env_none_when_only_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELAY_URL", RELAY_URL)
    monkeypatch.delenv("RELAY_TOKEN", raising=False)
    assert relay_transport_from_env() is None
