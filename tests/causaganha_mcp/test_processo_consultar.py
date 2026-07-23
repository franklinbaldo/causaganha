"""Behavior tests for the ``processo_consultar`` MCP tool (RFC 0014 M2).

`causaganha.processos.service.buscar_processo` itself is tested against real
local-parquet fixtures in `tests/causaganha/processos/test_service.py` — what
these tests own instead is the MCP-specific wiring layered on top of it:
mapping a `ProcessoConsultaResult` onto the Pydantic envelope
(`causaganha_mcp.tools.processo._to_result`), translating domain exceptions
into `fastmcp.exceptions.ToolError` without leaking upstream detail (same
philosophy as `test_datajud_facetas.py`), and building `web_url`/`web_path`
from the `CAUSAGANHA_WEB_BASE_URL` env var. `service.buscar_processo` is
monkeypatched at the tool module's own import (`causaganha_mcp.tools.processo
.service`) so none of this touches DuckDB or the network.
"""

from __future__ import annotations

import duckdb
import httpx
import pytest
from fastmcp.exceptions import ToolError

from causaganha.processos.models import (
    CnjInvalidoError,
    DatajudCapa,
    DjenResumo,
    DocumentoProcesso,
    FonteCobertura,
    JurisDecisao,
    ProcessoConsultaResult,
    StjAcordao,
)
from causaganha_mcp import server as server_module
from causaganha_mcp.tools import processo as processo_module


CNJ = "00000010220248220001"
CNJ_MASCARA = "0000001-02.2024.8.22.0001"


@pytest.fixture
def mcp():
    return server_module.build_server()


async def _processo_fn(mcp):
    tool = await mcp.get_tool("processo_consultar")
    return tool.fn


def _stub_returning(resultado: ProcessoConsultaResult):
    def _stub(*args: object, **kwargs: object) -> ProcessoConsultaResult:
        return resultado

    return _stub


def _stub_raising(exc: Exception):
    def _stub(*args: object, **kwargs: object) -> ProcessoConsultaResult:
        raise exc

    return _stub


def _resultado_encontrado(**overrides: object) -> ProcessoConsultaResult:
    base = {
        "encontrado": True,
        "nr_processo": CNJ,
        "nr_processo_mascara": CNJ_MASCARA,
        "fontes_presentes": ["datajud", "djen", "juris", "stj"],
        "cobertura_dataset": [FonteCobertura(fonte="djen", status="loaded_remote", registros=10)],
        "djen": DjenResumo(
            primeira_publicacao="2024-03-01",
            ultima_publicacao="2024-03-05",
            n_publicacoes=2,
            tribunais=["TJRO"],
        ),
        "juris": JurisDecisao(
            n_documentos=1,
            tipos=["ACÓRDÃO"],
            data_julgamento="2024-01-15",
            orgao="2a Camara",
            relator="Des. A",
            classe="Apelação",
            url="https://juris/1",
        ),
        "stj": StjAcordao(
            id="stj-1",
            classe="REsp",
            relator="MIN X",
            tema="tema",
            tese="tese",
            ementa="ementa",
            data_decisao="2024-05-01",
            data_publicacao="2024-05-10",
        ),
        "datajud": DatajudCapa(
            classe_oficial="Apelacao Civel",
            assuntos="Contratos",
            orgao_julgador="2a Camara",
            grau="G2",
            data_ajuizamento="2024-01-10",
            ultima_atualizacao="2024-06-01",
        ),
        "documentos": [
            DocumentoProcesso(
                fonte="stj",
                id_documento="stj-1",
                tipo="REsp",
                data="2024-05-01",
                url="",
                resumo="ementa",
            )
        ],
        "documentos_truncados": False,
        "dataset_gerado_em": "2026-07-12T18:00:00Z",
        "avisos": [],
    }
    base.update(overrides)
    return ProcessoConsultaResult(**base)


async def test_success_maps_every_field(mcp, monkeypatch) -> None:
    monkeypatch.delenv(processo_module._WEB_BASE_URL_ENV, raising=False)
    monkeypatch.setattr(
        processo_module.service, "buscar_processo", _stub_returning(_resultado_encontrado())
    )

    fn = await _processo_fn(mcp)
    result = fn(cnj=CNJ)

    assert result.encontrado is True
    assert result.cnj == CNJ
    assert result.cnj_formatado == CNJ_MASCARA
    assert result.fontes_presentes == ["datajud", "djen", "juris", "stj"]
    assert result.cobertura_dataset[0].fonte == "djen"
    assert result.cobertura_dataset[0].registros == 10

    assert result.djen.n_publicacoes == 2
    assert result.juris.orgao == "2a Camara"
    assert result.stj.id == "stj-1"
    assert result.datajud.classe_oficial == "Apelacao Civel"

    assert len(result.documentos) == 1
    assert result.documentos[0].fonte == "stj"
    assert result.documentos_truncados is False
    assert result.dataset_gerado_em == "2026-07-12T18:00:00Z"
    assert result.avisos == []

    assert result.fonte == "parquet_ia"
    assert result.canonica is True
    assert result.consultado_em  # a fresh timestamp, not empty
    assert result.web_path == f"/processo?cnj={CNJ_MASCARA}"
    assert result.web_url is None  # no env var set


async def test_not_found_leaves_optional_fields_empty(mcp, monkeypatch) -> None:
    resultado = ProcessoConsultaResult(
        encontrado=False, nr_processo=CNJ, nr_processo_mascara=CNJ_MASCARA
    )
    monkeypatch.setattr(processo_module.service, "buscar_processo", _stub_returning(resultado))

    fn = await _processo_fn(mcp)
    result = fn(cnj=CNJ)

    assert result.encontrado is False
    assert result.fontes_presentes == []
    assert result.cobertura_dataset == []
    assert result.djen is None
    assert result.juris is None
    assert result.stj is None
    assert result.datajud is None
    assert result.documentos == []
    assert result.avisos == []


async def test_web_url_built_from_env_var(mcp, monkeypatch) -> None:
    monkeypatch.setenv(processo_module._WEB_BASE_URL_ENV, "https://causaganha.example/")
    monkeypatch.setattr(
        processo_module.service, "buscar_processo", _stub_returning(_resultado_encontrado())
    )

    fn = await _processo_fn(mcp)
    result = fn(cnj=CNJ)

    assert result.web_url == f"https://causaganha.example/processo?cnj={CNJ_MASCARA}"


async def test_web_url_none_without_env_var(mcp, monkeypatch) -> None:
    monkeypatch.delenv(processo_module._WEB_BASE_URL_ENV, raising=False)
    monkeypatch.setattr(
        processo_module.service, "buscar_processo", _stub_returning(_resultado_encontrado())
    )

    fn = await _processo_fn(mcp)
    result = fn(cnj=CNJ)

    assert result.web_url is None


async def test_invalid_cnj_raises_tool_error_with_actionable_message(mcp, monkeypatch) -> None:
    exc = CnjInvalidoError("CNJ inválido (esperado 20 dígitos): '123'")
    monkeypatch.setattr(processo_module.service, "buscar_processo", _stub_raising(exc))

    fn = await _processo_fn(mcp)
    with pytest.raises(ToolError, match="CNJ inválido"):
        fn(cnj="123")


@pytest.mark.parametrize(
    "exc",
    [
        duckdb.Error("IO Error: could not open file /some/internal/path"),
        httpx.HTTPError("connection reset"),
    ],
)
async def test_source_failure_raises_generic_tool_error_without_leaking_detail(
    mcp, monkeypatch, exc
) -> None:
    monkeypatch.setattr(processo_module.service, "buscar_processo", _stub_raising(exc))

    fn = await _processo_fn(mcp)
    with pytest.raises(ToolError) as exc_info:
        fn(cnj=CNJ)

    message = str(exc_info.value)
    assert "indice_processual.parquet" in message
    assert "internal/path" not in message  # never leak the raw exception detail
    assert "connection reset" not in message
