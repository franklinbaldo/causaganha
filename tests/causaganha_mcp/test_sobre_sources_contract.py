"""Contract between the public "Como funciona" (sobre) page and the sources
the product actually queries.

Issue #1011 requires that once a TEOR dataset is wired into ``decisoes_buscar``
(TCU landed in #1021), the site presents it "onde houver busca/exploração de
TEOR" with the same coverage window as the MCP declares — never a different,
drifted claim. This mirrors the existing agentes.astro <-> build_server()
contract in test_web_agents_contract.py, applied to sobre.astro's source list.
"""

from __future__ import annotations

import re
from pathlib import Path

from causaganha_mcp.tools.decisoes import _datasets_for_source


_SOBRE_PAGE = Path(__file__).parents[2] / "web" / "src" / "pages" / "sobre.astro"

_FONTE_RE = re.compile(
    r"nome:\s*'([^']*)',\s*"
    r"prova:\s*'([^']*)',\s*"
    r"naoProva:\s*'([^']*)',\s*"
    r"papel:\s*'([^']*)',?",
    re.DOTALL,
)

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _parse_fontes() -> list[dict[str, str]]:
    text = _SOBRE_PAGE.read_text(encoding="utf-8")
    return [
        {"nome": nome, "prova": prova, "naoProva": nao_prova, "papel": papel}
        for nome, prova, nao_prova, papel in _FONTE_RE.findall(text)
    ]


def _mcp_declared_tcu_coverage_years() -> set[str]:
    _datasets, limitations = _datasets_for_source("tcu")
    tcu_limitation = next(text for text in limitations if "TCU" in text)
    return {m.group(0) for m in _YEAR_RE.finditer(tcu_limitation)}


def test_sobre_page_lists_tcu_as_a_teor_source() -> None:
    fontes = _parse_fontes()
    tcu = next((f for f in fontes if "TCU" in f["nome"]), None)
    assert tcu is not None, "sobre.astro deve listar TCU entre as fontes públicas"
    assert tcu["papel"] == "Teor"


def test_sobre_page_distinguishes_tcu_from_a_judicial_tribunal() -> None:
    fontes = _parse_fontes()
    tcu = next(f for f in fontes if "TCU" in f["nome"])
    combined = f"{tcu['prova']} {tcu['naoProva']}"
    assert "controle externo" in combined.lower(), (
        "TCU não é um tribunal judicial — a descrição do site deve deixar isso "
        "explícito, como já faz o limitacoes de decisoes_buscar"
    )


def test_sobre_page_tcu_coverage_window_matches_mcp() -> None:
    fontes = _parse_fontes()
    tcu = next(f for f in fontes if "TCU" in f["nome"])
    combined = f"{tcu['prova']} {tcu['naoProva']}"
    site_years = {m.group(0) for m in _YEAR_RE.finditer(combined)}

    mcp_years = _mcp_declared_tcu_coverage_years()

    assert mcp_years, "decisoes_buscar deve declarar uma janela de cobertura para TCU"
    assert mcp_years <= site_years, (
        f"cobertura TCU no site ({site_years}) diverge da cobertura declarada "
        f"pelo MCP ({mcp_years}) — issue #1011 exige que não haja drift"
    )
