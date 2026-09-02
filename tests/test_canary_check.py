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


def _install_json(monkeypatch, payload: dict[str, object]) -> None:
    def fake_get(*_args: object, **_kwargs: object) -> httpx.Response:
        return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://stj"))

    monkeypatch.setattr(canary_check.httpx, "get", fake_get)


def test_stj_published_artifact_with_data_passes(monkeypatch) -> None:
    _install_json(monkeypatch, {"total": 84, "total_temas": 15, "ultima_decisao": "20260623"})

    failures, warnings = canary_check.check_stj_published()

    assert failures == []
    assert warnings == []


def test_stj_published_artifact_empty_fails(monkeypatch) -> None:
    _install_json(monkeypatch, {"total": 0, "total_temas": 0, "ultima_decisao": None})

    failures, _ = canary_check.check_stj_published()

    assert any("total" in failure and "empty" in failure for failure in failures)


def test_stj_published_artifact_missing_field_fails(monkeypatch) -> None:
    _install_json(monkeypatch, {"total": 84})

    failures, _ = canary_check.check_stj_published()

    assert any("total_temas" in failure for failure in failures)


def test_stj_published_artifact_unreachable_fails(monkeypatch) -> None:
    def fake_get(*_args: object, **_kwargs: object) -> httpx.Response:
        return httpx.Response(500, request=httpx.Request("GET", "https://stj"))

    monkeypatch.setattr(canary_check.httpx, "get", fake_get)

    failures, _ = canary_check.check_stj_published()

    assert any("stj_totals.json" in failure for failure in failures)


def _juris_manifest_text(rows: int = 1) -> str:
    header = "tipo,mes_ano,ia_status,n_docs,updated_at"
    body = "\n".join(
        f"ACÓRDÃO,2026-0{i + 1},uploaded,1,2026-07-14T09:59:48+00:00" for i in range(rows)
    )
    return f"{header}\n{body}\n" if rows else f"{header}\n"


def test_tjro_juris_published_manifest_with_entries_passes(monkeypatch) -> None:
    monkeypatch.setattr(
        canary_check.tjro_juris_archive, "read_manifest_text", lambda: _juris_manifest_text(3)
    )

    failures, warnings = canary_check.check_tjro_juris_published()

    assert failures == []
    assert warnings == []


def test_tjro_juris_published_manifest_empty_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        canary_check.tjro_juris_archive, "read_manifest_text", lambda: _juris_manifest_text(0)
    )

    failures, _ = canary_check.check_tjro_juris_published()

    assert any("zero entries" in failure for failure in failures)


def test_tjro_juris_published_manifest_absent_fails(monkeypatch) -> None:
    monkeypatch.setattr(canary_check.tjro_juris_archive, "read_manifest_text", lambda: None)

    failures, _ = canary_check.check_tjro_juris_published()

    assert any(
        "tjro-juris-manifest.csv" in failure or "no TJRO JURIS manifest" in failure
        for failure in failures
    )


def test_tjro_juris_published_manifest_invalid_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        canary_check.tjro_juris_archive, "read_manifest_text", lambda: "not,the,right,header\n"
    )

    failures, _ = canary_check.check_tjro_juris_published()

    assert any("invalid" in failure for failure in failures)


def test_tjro_juris_published_manifest_unreachable_fails(monkeypatch) -> None:
    def fake_read() -> str | None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(canary_check.tjro_juris_archive, "read_manifest_text", fake_read)

    failures, _ = canary_check.check_tjro_juris_published()

    assert any("could not fetch" in failure for failure in failures)
