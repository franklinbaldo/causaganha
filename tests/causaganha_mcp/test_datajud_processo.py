"""Behavior tests for the agent-oriented ``datajud_processo`` tool."""

from __future__ import annotations

import pytest
import respx
from fastmcp.exceptions import ToolError

from causaganha_mcp.server import build_server
from causaganha_mcp.tools import datajud_processo as tool_module
from datajud.client import search_endpoint


ENDPOINT = search_endpoint("tjro")
CNJ = "00000010220248220001"


def _source(
    *,
    grau: str,
    orgao: str,
    atualizado: str,
    movimentos: list[dict],
) -> dict:
    return {
        "numeroProcesso": CNJ,
        "tribunal": "TJRO",
        "grau": grau,
        "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
        "assuntos": [{"codigo": 1, "nome": "Direito Administrativo"}],
        "orgaoJulgador": {"codigo": 10 if grau == "G1" else 20, "nome": orgao},
        "dataAjuizamento": "20240102030405",
        "dataHoraUltimaAtualizacao": atualizado,
        "movimentos": movimentos,
    }


def _payload() -> dict:
    return {
        "hits": {
            "hits": [
                {
                    "_source": _source(
                        grau="G1",
                        orgao="1ª Vara",
                        atualizado="2026-08-21T12:00:00Z",
                        movimentos=[
                            {
                                "codigo": 92,
                                "nome": "Publicação",
                                "dataHora": "2026-08-21T12:00:00Z",
                            },
                            {
                                "codigo": 51,
                                "nome": "Conclusão",
                                "dataHora": "2026-08-20T10:00:00Z",
                            },
                        ],
                    )
                },
                {
                    "_source": _source(
                        grau="G2",
                        orgao="2ª Câmara",
                        atualizado="2026-08-21T13:00:00Z",
                        movimentos=[
                            {
                                "codigo": 246,
                                "nome": "Julgamento",
                                "dataHora": "2026-08-21T13:00:00Z",
                                "complementosTabelados": [
                                    {"descricao": "resultado", "nome": "provido"}
                                ],
                            }
                        ],
                    )
                },
            ]
        }
    }


@pytest.fixture
def mcp():
    return build_server()


async def _fn(mcp):
    tool = await mcp.get_tool("datajud_processo")
    return tool.fn


async def test_datajud_processo_returns_summary_first_and_filters_noise(mcp) -> None:
    fn = await _fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json=_payload())
        result = await fn(cnj=CNJ, tribunal="tjro")

    assert result.encontrado is True
    assert result.natureza == "estado"
    assert result.tribunal == "tjro"
    assert result.total_movimentos == 3
    assert len(result.graus) == 2
    assert result.movimentos == []  # raw timeline is opt-in

    # Code 92 (Publicação) is routine noise for the compact marco view.
    assert [m.codigo for m in result.marcos] == [246, 51]
    assert result.ultimo_marco is not None
    assert result.ultimo_marco.codigo == 246
    assert result.ultimo_marco.grau == "G2"
    assert result.ultimo_marco.complementos == "resultado=provido"
    assert "Último marco: Julgamento" in result.resumo

    archive_action = next(a for a in result.next_actions if a.tool == "processo_consultar")
    assert archive_action.argumentos["cnj"] == result.cnj_formatado
    assert any("não contém" in item for item in result.limitacoes)


async def test_datajud_processo_full_movements_are_explicit_opt_in(mcp) -> None:
    fn = await _fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json=_payload())
        result = await fn(
            cnj=CNJ,
            tribunal="tjro",
            incluir_movimentos=True,
            limite_movimentos=10,
        )

    assert [m.codigo for m in result.movimentos] == [246, 92, 51]
    assert result.movimentos_truncados is False


async def test_datajud_processo_last_marco_is_computed_across_all_graus(mcp) -> None:
    fn = await _fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json=_payload())
        result = await fn(cnj=CNJ, tribunal="tjro", limite_marcos=1)

    assert len(result.marcos) == 1
    assert result.marcos_truncados is True
    assert result.ultimo_marco is not None
    assert result.ultimo_marco.data_hora == "2026-08-21T13:00:00Z"


async def test_datajud_processo_not_found_is_not_process_nonexistence(mcp) -> None:
    fn = await _fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        result = await fn(cnj=CNJ, tribunal="tjro")

    assert result.encontrado is False
    assert "não retornou registro" in result.resumo
    assert any("não significa" in item for item in result.limitacoes)
    assert result.next_actions[0].tool == "processo_consultar"


async def test_datajud_processo_rejects_invalid_cnj_before_network(mcp) -> None:
    fn = await _fn(mcp)
    with respx.mock(assert_all_called=False) as router:
        route = router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        with pytest.raises(ToolError, match="CNJ inválido"):
            await fn(cnj="123", tribunal="tjro")
        assert route.called is False


async def test_datajud_processo_has_hard_interactive_timeout(mcp) -> None:
    tool = await mcp.get_tool("datajud_processo")
    assert tool.timeout == tool_module._PROCESSO_TOOL_TIMEOUT


async def test_datajud_processo_auth_failure_is_actionable(mcp) -> None:
    fn = await _fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(401)
        with pytest.raises(ToolError, match="401"):
            await fn(cnj=CNJ, tribunal="tjro")
