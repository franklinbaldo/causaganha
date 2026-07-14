"""Tests for the Cloud Run relay function (deployment/relay/function/main.py).

Exercises the actual security boundary — host allowlist, token auth, and
header stripping — which tests/common/test_relay.py can't reach since it
only covers the client-side RelayTransport (which just rewrites headers and
always defers to the relay). Uses Werkzeug's Request/EnvironBuilder to build
real Flask Request objects (the same type functions_framework hands the
handler) and monkeypatches the module's shared httpx client so no real
network call happens.
"""

from __future__ import annotations

import gzip

import httpx
import pytest
from flask import Request
from werkzeug.test import EnvironBuilder

from deployment.relay.function import main


RELAY_TOKEN = "s3cr3t-token"  # noqa: S105 — test fixture, not a real credential


def _request(
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> Request:
    builder = EnvironBuilder(method=method, headers=headers or {}, data=data)
    return Request(builder.get_environ())


@pytest.fixture(autouse=True)
def _relay_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "_RELAY_TOKEN", RELAY_TOKEN)


# ── _host_allowed ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "hostname",
    [
        "stj.jus.br",
        "scon.stj.jus.br",
        "dadosabertos.web.stj.jus.br",
        "tjro.jus.br",
        "juris-back.tjro.jus.br",
        "STJ.JUS.BR",
    ],
)
def test_host_allowed_accepts_allowlisted_hosts(hostname: str) -> None:
    assert main._host_allowed(hostname) is True


@pytest.mark.parametrize(
    "hostname",
    [
        None,
        "",
        "example.com",
        "evilstj.jus.br",
        "stj.jus.br.attacker.com",
        "notstj.jus.br.evil.com",
    ],
)
def test_host_allowed_rejects_everything_else(hostname: str | None) -> None:
    assert main._host_allowed(hostname) is False


# ── _token_valid ─────────────────────────────────────────────────────────


def test_token_valid_accepts_correct_token() -> None:
    request = _request(headers={"X-Relay-Token": RELAY_TOKEN})
    assert main._token_valid(request) is True


def test_token_valid_rejects_wrong_token() -> None:
    request = _request(headers={"X-Relay-Token": "wrong"})
    assert main._token_valid(request) is False


def test_token_valid_rejects_missing_token() -> None:
    request = _request()
    assert main._token_valid(request) is False


def test_token_valid_rejects_when_relay_token_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "_RELAY_TOKEN", "")
    request = _request(headers={"X-Relay-Token": "anything"})
    assert main._token_valid(request) is False


# ── _forward_headers ─────────────────────────────────────────────────────


def test_forward_headers_strips_hop_by_hop_and_relay_headers() -> None:
    request = _request(
        headers={
            "X-Relay-Token": RELAY_TOKEN,
            "X-Relay-Url": "https://scon.stj.jus.br/",
            "Connection": "keep-alive",
            "Accept": "application/json",
        }
    )
    headers = main._forward_headers(request, "scon.stj.jus.br")
    assert "X-Relay-Token" not in headers
    assert "X-Relay-Url" not in headers
    assert "Connection" not in headers
    assert "Content-Length" not in headers
    assert headers["Accept"] == "application/json"
    assert headers["Host"] == "scon.stj.jus.br"


# ── relay() end-to-end (monkeypatched upstream client) ────────────────────


def test_relay_rejects_missing_token() -> None:
    request = _request()
    _body, status = main.relay(request)
    assert status == 401


def test_relay_rejects_off_allowlist_host() -> None:
    request = _request(
        headers={"X-Relay-Token": RELAY_TOKEN, "X-Relay-Url": "https://example.com/"}
    )
    _body, status = main.relay(request)
    assert status == 403


def test_relay_rejects_missing_url() -> None:
    request = _request(headers={"X-Relay-Token": RELAY_TOKEN})
    _body, status = main.relay(request)
    assert status == 403


def test_relay_rejects_non_http_scheme() -> None:
    request = _request(headers={"X-Relay-Token": RELAY_TOKEN, "X-Relay-Url": "file:///etc/passwd"})
    _body, status = main.relay(request)
    assert status == 403


def test_relay_forwards_to_upstream_and_strips_content_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(req)
        return httpx.Response(
            200,
            content=gzip.compress(b'{"ok": true}'),
            headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
        )

    monkeypatch.setattr(main, "_client", httpx.Client(transport=httpx.MockTransport(handler)))

    request = _request(
        headers={
            "X-Relay-Token": RELAY_TOKEN,
            "X-Relay-Url": "https://scon.stj.jus.br/api/resource",
            "Accept": "application/json",
        }
    )
    body, status, headers = main.relay(request)

    assert status == 200
    assert body == b'{"ok": true}'
    assert "content-encoding" not in headers
    assert headers["content-type"] == "application/json"
    assert len(captured) == 1
    assert str(captured[0].url) == "https://scon.stj.jus.br/api/resource"
    assert captured[0].headers["Host"] == "scon.stj.jus.br"


def test_relay_returns_502_on_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        message = "boom"
        raise httpx.ConnectTimeout(message, request=req)

    monkeypatch.setattr(main, "_client", httpx.Client(transport=httpx.MockTransport(handler)))

    request = _request(
        headers={"X-Relay-Token": RELAY_TOKEN, "X-Relay-Url": "https://scon.stj.jus.br/"}
    )
    _body, status = main.relay(request)
    assert status == 502
