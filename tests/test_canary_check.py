"""Tests for business-day freshness in the deployed-system canary."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from holidays import Brazil

from scripts import canary_check


def _status(last_success_at: str, pending_real: int = 0) -> dict[str, object]:
    return {
        "generated_at": "2026-08-10T11:30:00Z",
        "sources": {
            "djen": {
                "last_success_at": last_success_at,
                "coverage_pct": 25.0,
                "pairs_total": 100,
                "tribunals_total": 10,
                "pending_real": pending_real,
            }
        },
    }


def _install_status(monkeypatch, payload: dict[str, object]) -> None:
    def fake_get(*_args: object, **_kwargs: object) -> httpx.Response:
        return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://status"))

    monkeypatch.setattr(canary_check.httpx, "get", fake_get)


def test_friday_success_is_fresh_on_monday_despite_wall_clock_age(monkeypatch) -> None:
    _install_status(monkeypatch, _status("2026-08-07T03:00:00Z"))

    failures, _ = canary_check.check_site_status(
        datetime(2026, 8, 10, 12, 30, tzinfo=UTC), Brazil()
    )

    assert failures == []


def test_friday_success_is_stale_on_tuesday(monkeypatch) -> None:
    payload = _status("2026-08-07T03:00:00Z")
    payload["generated_at"] = "2026-08-11T11:30:00Z"
    _install_status(monkeypatch, payload)

    failures, _ = canary_check.check_site_status(
        datetime(2026, 8, 11, 12, 30, tzinfo=UTC), Brazil()
    )

    assert any("expected business day 2026-08-10" in failure for failure in failures)


def test_business_day_success_does_not_hide_stale_deploy(monkeypatch) -> None:
    payload = _status("2026-08-10T03:00:00Z")
    payload["generated_at"] = "2026-08-08T00:00:00Z"
    _install_status(monkeypatch, payload)

    failures, _ = canary_check.check_site_status(
        datetime(2026, 8, 11, 12, 30, tzinfo=UTC), Brazil()
    )

    assert any("deploy-web pipeline appears stalled" in failure for failure in failures)


def test_pending_real_within_threshold_passes(monkeypatch) -> None:
    payload = _status(
        "2026-08-10T03:00:00Z",
        pending_real=canary_check.PENDING_REAL_THRESHOLD,
    )
    _install_status(monkeypatch, payload)

    failures, _ = canary_check.check_site_status(
        datetime(2026, 8, 11, 12, 30, tzinfo=UTC), Brazil()
    )

    assert not any("pending_real" in failure for failure in failures)


def test_pending_real_above_threshold_fails(monkeypatch) -> None:
    payload = _status(
        "2026-08-10T03:00:00Z",
        pending_real=canary_check.PENDING_REAL_THRESHOLD + 1,
    )
    _install_status(monkeypatch, payload)

    failures, _ = canary_check.check_site_status(
        datetime(2026, 8, 11, 12, 30, tzinfo=UTC), Brazil()
    )

    assert any(
        "pending_real" in failure and "publication→archive backlog" in failure
        for failure in failures
    )
