"""Tests for scripts/render_contract_fixture.py's real-network guard.

Regression coverage for the incident that closed PR #1356: a fixture source
missing an isolation entry fell through to a real, slow IA download inside
the vitest sandbox instead of failing fast. See knowledge/agent-runs/
2026-09-09-exciting-mccarthy-0lpi0s/goals/goal-fixture-network-guard.md.
"""

from __future__ import annotations

import httpx
import pytest

from scripts import render_contract_fixture as fixture
from scripts import render_queries as renderer


def test_block_real_network_blocks_urlopen():
    with fixture._block_real_network():
        with pytest.raises(fixture.RealNetworkAccessError):
            renderer.urllib.request.urlopen("https://example.invalid/blocked")


def test_block_real_network_blocks_httpx():
    with fixture._block_real_network():
        with pytest.raises(fixture.RealNetworkAccessError):
            with httpx.Client() as client:
                client.get("https://example.invalid/blocked")


def test_block_real_network_restores_originals_on_exit():
    real_urlopen = renderer.urllib.request.urlopen
    real_send = httpx.Client.send
    with fixture._block_real_network():
        pass
    assert renderer.urllib.request.urlopen is real_urlopen
    assert httpx.Client.send is real_send


def test_render_fixture_fails_fast_when_a_source_input_is_missing(tmp_path, monkeypatch):
    """Simulate a fixture forgetting to isolate one source's local input.

    Before this guard, a source falling through to real IA/network access
    either hung for 100+ seconds (reconcile_processos.ensure_*_parquets, the
    PR #1356 incident) or silently degraded to an 'optional contract
    skipped' warning (_try_download_parquet's own OSError handling) --
    neither is acceptable in a fixture that must never touch the network.
    Deleting the manifest's local fixture input after _write_fixtures()
    forces _register_manifest to fall through to _try_download_parquet's
    real urllib.request.urlopen call, which the guard must intercept and
    turn into an immediate, clearly-diagnosed failure instead.
    """
    output_dir = tmp_path / "fixture"
    fixtures_dir = output_dir / "fixtures"
    fixture._write_fixtures(fixtures_dir)

    monkeypatch.setattr(renderer, "ROOT", fixtures_dir)
    monkeypatch.setattr(
        renderer, "LOCAL_MANIFEST_PARQUET", fixtures_dir / "data" / "sync-manifest.parquet"
    )
    monkeypatch.setattr(renderer, "DEV_RATINGS_DIR", fixtures_dir / "data/parquets")
    monkeypatch.setattr(renderer, "_STJ_PARQUET", fixtures_dir / "data/stj/stj-acordaos.parquet")
    (fixtures_dir / "data" / "sync-manifest.parquet").unlink()

    with fixture._block_real_network(), pytest.raises(fixture.RealNetworkAccessError):
        renderer.render_all(public_dir=output_dir / "web/public")


def test_render_fixture_end_to_end_never_touches_real_network(tmp_path):
    fixture.render_fixture(tmp_path)
    assert (tmp_path / "query-contracts.json").exists()


def test_render_fixture_does_not_leak_patched_state_to_the_process(tmp_path):
    """render_fixture() must not permanently overwrite the real modules it patches.

    render_fixture() used to reassign renderer.ROOT/_register_comunicacoes and
    reconcile_processos.ensure_juris_parquets/ensure_datajud_parquets directly,
    with no restore. Calling it in-process (as this test does, unlike the
    vitest integration test which always spawns a subprocess) permanently
    replaced the real functions for the rest of this pytest process — which is
    exactly what made tests/test_render_queries.py's own
    test_register_comunicacoes_* tests fail once this file's tests ran first.
    """
    real_register_comunicacoes = renderer._register_comunicacoes
    real_ensure_juris_parquets = renderer.reconcile_processos.ensure_juris_parquets
    real_ensure_datajud_parquets = renderer.reconcile_processos.ensure_datajud_parquets
    real_root = renderer.ROOT

    fixture.render_fixture(tmp_path)

    assert renderer._register_comunicacoes is real_register_comunicacoes
    assert renderer.reconcile_processos.ensure_juris_parquets is real_ensure_juris_parquets
    assert renderer.reconcile_processos.ensure_datajud_parquets is real_ensure_datajud_parquets
    assert renderer.ROOT == real_root
