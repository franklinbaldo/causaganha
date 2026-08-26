"""Clock-specific tests for the aggregate pipeline status."""

from __future__ import annotations

from types import SimpleNamespace

import httpx

import causaganha_mcp.tools.status as status_module


def test_published_object_clock_reads_last_modified(monkeypatch):
    response = httpx.Response(
        200,
        headers={"Last-Modified": "Wed, 26 Aug 2026 14:12:00 GMT"},
        request=httpx.Request("HEAD", "https://archive.org/object"),
    )
    monkeypatch.setattr(status_module.httpx, "head", lambda *_args, **_kwargs: response)

    state, timestamp, warning = status_module._published_object_clock("https://archive.org/object")

    assert state == "present"
    assert timestamp == "2026-08-26T14:12:00+00:00"
    assert warning is None


def test_published_object_clock_preserves_unknown_without_header(monkeypatch):
    response = httpx.Response(200, request=httpx.Request("HEAD", "https://archive.org/object"))
    monkeypatch.setattr(status_module.httpx, "head", lambda *_args, **_kwargs: response)

    state, timestamp, warning = status_module._published_object_clock("https://archive.org/object")

    assert state == "unknown"
    assert timestamp is None
    assert "Last-Modified" in warning


def test_execution_clock_is_composed_without_overwriting_publication(monkeypatch):
    pipeline = status_module.PipelineStatus(
        nome="djen",
        observacao="present",
        encontrado=True,
        total=1,
        contagens={"enviados": 1},
        fonte="manifest_publicado",
        canonica=True,
        publicacao_observacao="unknown",
        publicacao_aviso="composite authority",
    )
    metadata = (
        status_module.knowledge.PipelineMetadata(
            nome="djen",
            fonte="DJEN",
            pacote="djen_backup",
            mcp_status="djen_backup_status",
            workflow=".github/workflows/collect-zips.yml",
            cadencia_cron="*/20 * * * *",
            tentativa_semantica="run starts",
            sucesso_semantica="run succeeds",
            publicacao_semantica="published authority changes",
            canario_semantica="existing E2E",
        ),
    )
    monkeypatch.setattr(
        status_module,
        "pipeline_status_loaders",
        lambda: (("djen_backup_status", lambda: pipeline),),
    )
    monkeypatch.setattr(
        status_module.workflow_runs,
        "observe_workflow_runs",
        lambda _workflow: SimpleNamespace(
            observacao="present",
            ultima_tentativa="2026-08-26T14:00:00+00:00",
            ultimo_sucesso="2026-08-26T14:02:00+00:00",
            aviso=None,
        ),
    )

    [result] = status_module._pipeline_statuses(metadata)

    assert result.execucao_observacao == "present"
    assert result.ultima_tentativa == "2026-08-26T14:00:00+00:00"
    assert result.ultimo_sucesso == "2026-08-26T14:02:00+00:00"
    assert result.publicacao_observacao == "unknown"
    assert result.ultima_publicacao is None
