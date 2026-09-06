"""Canonical example questions for the public `/agentes` onboarding page (#1217).

Each entry pairs the natural-language question a person can copy-paste to an
agent with the MCP tool it must exercise. This module is the single authority
for that wording: `web/src/pages/agentes.astro` embeds the same text verbatim
as a static attribute, and `tests/causaganha_mcp/test_agents_page_examples_contract.py`
fails if the page ever drifts from it, or if a listed tool stops existing in
`causaganha_mcp.server.build_server()`'s live catalog.

The CNJ used is not live data — it is the same fictitious-but-deterministic
fixture already reused across the MCP tool test suite (`test_processo_consultar
.py`, `test_publicacoes_buscar.py`, `test_processo_next_actions.py`,
`test_arquivo_estado_teor_contract.py`), derived here from the same raw digits
rather than re-typing the masked form, so the two can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from causaganha.processos.cnj import formatar_cnj


GOLDEN_CNJ = "00000010220248220001"
GOLDEN_CNJ_MASCARA = formatar_cnj(GOLDEN_CNJ)
GOLDEN_TRIBUNAL = "tjro"


@dataclass(frozen=True, slots=True)
class AgentJobExample:
    """One copyable example question shown under a job card on `/agentes`."""

    tool: str
    role: str
    pergunta: str


AGENT_JOB_EXAMPLES: tuple[AgentJobExample, ...] = (
    AgentJobExample(
        tool="processo_consultar",
        role="ARQUIVO",
        pergunta=f"O que o CausaGanha preservou sobre o processo {GOLDEN_CNJ_MASCARA}?",
    ),
    AgentJobExample(
        tool="publicacoes_buscar",
        role="ARQUIVO",
        pergunta=f"Quais publicações foram preservadas para o processo {GOLDEN_CNJ_MASCARA}?",
    ),
    AgentJobExample(
        tool="processo_estado",
        role="ESTADO",
        pergunta=(
            f"Qual é o estado processual disponível no DataJud para o processo "
            f"{GOLDEN_CNJ_MASCARA} no {GOLDEN_TRIBUNAL.upper()}?"
        ),
    ),
    AgentJobExample(
        tool="decisoes_buscar",
        role="TEOR",
        pergunta="Existe alguma decisão do STJ sobre dano moral no acervo?",
    ),
)
