"""Contract tests for the OKF-backed aggregate pipeline catalog (#877)."""

from __future__ import annotations

import inspect

import pytest

from causaganha_mcp.knowledge import PipelineMetadata, load_pipeline_metadata
from causaganha_mcp.tools import status_catalog


_EXPECTED = {
    ("djen", "djen", "djen_backup", "djen_backup_status"),
    ("tjro_juris", "tjro_juris", "tjro_juris", "tjro_juris_status"),
    ("stj_acordaos", "stj_acordaos", "stj_acordaos", "stj_acordaos_status"),
    ("datajud", "datajud", "datajud", "datajud_status"),
}


def test_pipeline_relation_is_a_real_typed_runtime_catalog() -> None:
    metadata = load_pipeline_metadata()
    observed = {(item.nome, item.fonte, item.pacote, item.mcp_status) for item in metadata}
    assert observed == _EXPECTED


def test_catalog_divergence_fails_explicitly_instead_of_using_a_hidden_fallback() -> None:
    metadata = tuple(
        PipelineMetadata(nome=nome, fonte=fonte, pacote=pacote, mcp_status=tool)
        for nome, fonte, pacote, tool in sorted(_EXPECTED)
    )
    broken = tuple(
        item.model_copy(update={"pacote": "pacote_errado"})
        if item.mcp_status == "djen_backup_status"
        else item
        for item in metadata
    )

    with pytest.raises(RuntimeError, match="declares unavailable package"):
        status_catalog._pipeline_statuses(broken)


def test_catalog_dispatch_remains_in_process_and_never_recurses_through_mcp() -> None:
    source = inspect.getsource(status_catalog)
    assert "get_tool" not in source
    assert "call_tool" not in source
    assert "Client(" not in source
    assert "import_module" in source
    assert 'f"{item.pacote}.service"' in source
