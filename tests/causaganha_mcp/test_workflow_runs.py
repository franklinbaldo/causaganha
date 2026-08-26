"""Tests for bounded GitHub Actions attempt/success observation (#892)."""

from __future__ import annotations

import httpx

from causaganha_mcp.workflow_runs import observe_workflow_runs


def _client(payload: dict, status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/actions/workflows/collect-zips.yml/runs")
        return httpx.Response(status_code, json=payload, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_observes_schedule_attempt_and_success_as_distinct_clocks() -> None:
    payload = {
        "total_count": 3,
        "workflow_runs": [
            {
                "event": "schedule",
                "conclusion": "failure",
                "run_started_at": "2026-08-26T02:00:00Z",
                "created_at": "2026-08-26T01:59:58Z",
                "updated_at": "2026-08-26T02:02:00Z",
            },
            {
                "event": "workflow_dispatch",
                "conclusion": "success",
                "run_started_at": "2026-08-26T01:00:00Z",
                "created_at": "2026-08-26T00:59:58Z",
                "updated_at": "2026-08-26T01:04:00Z",
            },
            {
                "event": "push",
                "conclusion": "success",
                "run_started_at": "2026-08-26T02:30:00Z",
                "created_at": "2026-08-26T02:29:58Z",
                "updated_at": "2026-08-26T02:31:00Z",
            },
        ],
    }
    with _client(payload) as client:
        result = observe_workflow_runs(".github/workflows/collect-zips.yml", client=client)

    assert result.observacao == "present"
    assert result.ultima_tentativa == "2026-08-26T02:00:00Z"
    assert result.ultimo_sucesso == "2026-08-26T01:04:00Z"
    assert result.runs_observados == 3
    assert result.janela_completa is True
    assert result.aviso is None


def test_push_success_never_counts_as_pipeline_success() -> None:
    payload = {
        "total_count": 1,
        "workflow_runs": [
            {
                "event": "push",
                "conclusion": "success",
                "run_started_at": "2026-08-26T02:30:00Z",
                "updated_at": "2026-08-26T02:31:00Z",
            }
        ],
    }
    with _client(payload) as client:
        result = observe_workflow_runs(".github/workflows/collect-zips.yml", client=client)

    assert result.observacao == "unknown"
    assert result.ultima_tentativa is None
    assert result.ultimo_sucesso is None
    assert result.janela_completa is True


def test_no_success_in_truncated_window_is_not_false_absence() -> None:
    payload = {
        "total_count": 150,
        "workflow_runs": [
            {
                "event": "schedule",
                "conclusion": "failure",
                "run_started_at": "2026-08-26T02:00:00Z",
                "updated_at": "2026-08-26T02:02:00Z",
            }
        ],
    }
    with _client(payload) as client:
        result = observe_workflow_runs(".github/workflows/collect-zips.yml", client=client, limit=1)

    assert result.observacao == "present"
    assert result.ultima_tentativa == "2026-08-26T02:00:00Z"
    assert result.ultimo_sucesso is None
    assert result.janela_completa is False
    assert "sucesso anterior" in (result.aviso or "")


def test_zero_total_is_the_only_absent_state() -> None:
    with _client({"total_count": 0, "workflow_runs": []}) as client:
        result = observe_workflow_runs(".github/workflows/collect-zips.yml", client=client)

    assert result.observacao == "absent"
    assert result.janela_completa is True
    assert result.runs_observados == 0


def test_transport_failure_is_unavailable_not_absent() -> None:
    with _client({"message": "boom"}, status_code=503) as client:
        result = observe_workflow_runs(".github/workflows/collect-zips.yml", client=client)

    assert result.observacao == "unavailable"
    assert result.ultima_tentativa is None
    assert result.ultimo_sucesso is None
    assert result.janela_completa is False


def test_malformed_success_response_is_unavailable() -> None:
    with _client({"total_count": 10}) as client:
        result = observe_workflow_runs(".github/workflows/collect-zips.yml", client=client)

    assert result.observacao == "unavailable"


def test_limit_is_bounded_by_github_api_contract() -> None:
    for invalid in (0, 101):
        try:
            observe_workflow_runs(".github/workflows/collect-zips.yml", limit=invalid)
        except ValueError as exc:
            assert "between 1 and 100" in str(exc)
        else:  # pragma: no cover - assertion aid
            raise AssertionError("invalid limit must fail before network")
