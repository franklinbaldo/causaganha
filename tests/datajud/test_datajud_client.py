"""Tests for datajud.client — both rate-limit flavors, batching, auth errors.

Error discipline (RFC 0010): HTTP status is not a verdict. A 200 body can
carry an ES rejection — it must be retried and, when the budget is
exhausted, raise a nominal error. It must NEVER be treated as success.
Zero real network (respx).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
import tenacity

from causaganha.config import DATAJUD_PUBLIC_API_KEY_DEFAULT
from datajud.client import (
    API_KEY_ENV,
    DataJudAuthError,
    DataJudClient,
    DataJudError,
    DataJudRateLimitError,
    get_api_key,
    is_es_error,
    is_es_rejection,
    retry_wait,
    search_endpoint,
)


ENDPOINT = search_endpoint("tjro")
TEST_API_KEY = "test-datajud-api-key"

CNJ_A = "00000010220248220001"
CNJ_B = "00000020320248220002"
CNJ_C = "00000030420248220003"

ES_REJECTION_BODY = {
    "error": {
        "root_cause": [
            {
                "type": "es_rejected_execution_exception",
                "reason": "rejected execution of coordinating operation",
            }
        ],
        "type": "search_phase_execution_exception",
    },
    "status": 429,
}

OK_BODY = {"hits": {"total": {"value": 0, "relation": "eq"}, "hits": []}}


def _client(**kwargs: object) -> DataJudClient:
    defaults: dict = {
        "tribunal": "tjro",
        "api_key": TEST_API_KEY,
        "backoff_base": 0.0,
        "batch_pause": 0.0,
        "requests_per_minute": 100_000,
    }
    defaults.update(kwargs)
    return DataJudClient(**defaults)


def _hits(sources: list[dict]) -> dict:
    return {
        "hits": {
            "total": {"value": len(sources), "relation": "eq"},
            "hits": [{"_id": f"id-{i}", "_source": s} for i, s in enumerate(sources)],
        }
    }


# ── Rate limit flavor 1: HTTP 429 ────────────────────────────────────────


async def test_429_is_retried_then_succeeds():
    with respx.mock() as router:
        route = router.post(ENDPOINT)
        route.side_effect = [httpx.Response(429), httpx.Response(200, json=OK_BODY)]
        async with _client() as client:
            payload = await client.search({"query": {"match_all": {}}})

    assert payload == OK_BODY
    assert route.call_count == 2


async def test_persistent_429_raises_rate_limit_error():
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(429)
        async with _client(max_retries=3) as client:
            with pytest.raises(DataJudRateLimitError, match="429"):
                await client.search({"query": {"match_all": {}}})

    # initial attempt + 3 retries
    assert route.call_count == 4


def test_backoff_is_exponential_and_capped():
    """The retry wait doubles per attempt and is capped at 30s."""
    wait = retry_wait(2.0)
    delays = []
    for attempt in (1, 2, 3, 4, 10):
        state = tenacity.RetryCallState(None, None, (), {})
        state.attempt_number = attempt
        delays.append(wait(state))
    assert delays == [2.0, 4.0, 8.0, 16.0, 30.0]


# ── Rate limit flavor 2: ES rejection inside an HTTP 200 body ────────────


def test_is_es_rejection_detects_the_200_flavor():
    assert is_es_rejection(ES_REJECTION_BODY) is True
    assert is_es_rejection(OK_BODY) is False
    assert is_es_rejection(None) is False
    assert is_es_rejection({"error": "string error"}) is False


# ── Non-rejection ES errors inside an HTTP 200 body ──────────────────────
# A 200 can carry an ES error that is NOT the queue-full flavor (e.g. a
# malformed query, a shard failure). That must never be silently treated as
# a normal (empty) result — is_es_rejection() alone can't tell, since it
# only recognizes "rejected_execution".


def test_is_es_error_detects_any_error_body():
    assert is_es_error(ES_REJECTION_BODY) is True
    other_error = {"error": {"root_cause": [{"type": "query_shard_exception"}]}}
    assert is_es_error(other_error) is True
    assert is_es_error(OK_BODY) is False
    assert is_es_error(None) is False


async def test_non_rejection_es_error_in_200_raises_nominally_not_silently_empty():
    other_error = {"error": {"root_cause": [{"type": "query_shard_exception"}]}, "status": 400}
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=other_error)
        async with _client() as client:
            with pytest.raises(DataJudError, match="query_shard_exception"):
                await client.search({"query": {"match_all": {}}})

    # Non-transient ES error: NOT retried (unlike the rejected_execution flavor).
    assert route.call_count == 1


async def test_es_rejection_in_200_is_retried_then_succeeds():
    with respx.mock() as router:
        route = router.post(ENDPOINT)
        route.side_effect = [
            httpx.Response(200, json=ES_REJECTION_BODY),
            httpx.Response(200, json=OK_BODY),
        ]
        async with _client() as client:
            payload = await client.search({"query": {"match_all": {}}})

    assert payload == OK_BODY
    assert route.call_count == 2


async def test_persistent_es_rejection_raises_never_returns_body():
    """An exhausted ES-rejection budget is a nominal error — NEVER a success."""
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=ES_REJECTION_BODY)
        async with _client(max_retries=2) as client:
            with pytest.raises(DataJudRateLimitError, match="es_rejected_execution_exception"):
                await client.search({"query": {"match_all": {}}})

    assert route.call_count == 3


# ── 401: nominal auth error, no retry ────────────────────────────────────


async def test_401_raises_nominal_auth_error_without_retry():
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(401)
        async with _client() as client:
            with pytest.raises(DataJudAuthError, match=API_KEY_ENV):
                await client.search({"query": {"match_all": {}}})

    assert route.call_count == 1


# ── API key resolution ───────────────────────────────────────────────────


def test_api_key_absent_uses_configured_public_default(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    assert get_api_key() == DATAJUD_PUBLIC_API_KEY_DEFAULT


def test_api_key_env_override(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, "rotated-key")
    assert get_api_key() == "rotated-key"


async def test_authorization_header_uses_apikey_scheme():
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=OK_BODY)
        async with _client() as client:
            await client.search({"query": {"match_all": {}}})

    request = route.calls.last.request
    assert request.headers["Authorization"] == f"APIKey {TEST_API_KEY}"


# ── Batch CNJ lookup + pagination ────────────────────────────────────────


async def test_fetch_processos_batches_terms_and_paginates():
    """3 CNJs, batch_size=2, page_size=2 → 2 batches; first batch paginates."""
    source = {"numeroProcesso": CNJ_A, "grau": "G1"}
    with respx.mock() as router:
        route = router.post(ENDPOINT)
        route.side_effect = [
            # batch 1, page 1: full page → triggers page 2
            httpx.Response(200, json=_hits([source, source])),
            # batch 1, page 2: short page → stop
            httpx.Response(200, json=_hits([source])),
            # batch 2, page 1: short page → stop
            httpx.Response(200, json=_hits([source])),
        ]
        async with _client(batch_size=2, page_size=2) as client:
            sources = await client.fetch_processos([CNJ_A, CNJ_B, CNJ_C])

    assert len(sources) == 4
    assert route.call_count == 3

    bodies = [json.loads(call.request.content) for call in route.calls]
    # terms query on numeroProcesso, never one request per CNJ
    assert bodies[0]["query"]["terms"]["numeroProcesso"] == [CNJ_A, CNJ_B]
    assert bodies[1]["query"]["terms"]["numeroProcesso"] == [CNJ_A, CNJ_B]
    assert bodies[2]["query"]["terms"]["numeroProcesso"] == [CNJ_C]
    # pagination via from/size within the batch
    assert bodies[0]["from"] == 0
    assert bodies[1]["from"] == 2
    assert bodies[2]["from"] == 0
    # track_total_hits always true (totals saturate at 10k otherwise)
    assert all(body["track_total_hits"] is True for body in bodies)


async def test_fetch_processos_normalizes_and_dedupes_cnjs():
    masked = "0000001-02.2024.8.22.0001"  # same as CNJ_A, masked
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=_hits([]))
        async with _client() as client:
            await client.fetch_processos([masked, CNJ_A, "invalid", "123"])

    assert route.call_count == 1
    body = json.loads(route.calls.last.request.content)
    assert body["query"]["terms"]["numeroProcesso"] == [CNJ_A]


async def test_fetch_processos_no_valid_cnjs_makes_no_requests():
    with respx.mock(assert_all_called=False) as router:
        router.post(ENDPOINT).respond(200, json=_hits([]))
        async with _client() as client:
            assert await client.fetch_processos(["nope", ""]) == []

    assert not router.calls


# ── Facetas ──────────────────────────────────────────────────────────────


async def test_facetas_uses_keyword_field_and_parses_buckets():
    body = {
        "hits": {"total": {"value": 1000, "relation": "eq"}, "hits": []},
        "aggregations": {
            "facetas": {
                "buckets": [
                    {"key": "Procedimento Comum Cível", "doc_count": 700},
                    {"key": "Execução Fiscal", "doc_count": 300},
                ]
            }
        },
    }
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=body)
        async with _client() as client:
            total, buckets = await client.facetas("classe", limite=2)

    assert total == 1000
    assert buckets == [
        {"chave": "Procedimento Comum Cível", "qtd": 700},
        {"chave": "Execução Fiscal", "qtd": 300},
    ]
    sent = json.loads(route.calls.last.request.content)
    # text fields must be aggregated via .keyword (raw text field → HTTP 400)
    assert sent["aggs"]["facetas"]["terms"]["field"] == "classe.nome.keyword"
    assert sent["size"] == 0


# ── Transport errors ─────────────────────────────────────────────────────


async def test_transport_error_is_retried_then_succeeds():
    with respx.mock() as router:
        route = router.post(ENDPOINT)
        route.side_effect = [httpx.ConnectTimeout("slow"), httpx.Response(200, json=OK_BODY)]
        async with _client() as client:
            payload = await client.search({"query": {"match_all": {}}})

    assert payload == OK_BODY
    assert route.call_count == 2
