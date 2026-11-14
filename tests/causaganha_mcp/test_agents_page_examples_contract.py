"""Contract for the example questions of the public MCP jobs (#1217).

`test_web_agents_contract.py` gates the README's job/role list against the
live public catalog and the published-fontes authority. This file covers the
per-job example question: `agents_examples.AGENT_JOB_EXAMPLES` is the single
authority for the wording, and each example must name a registered MCP tool.
"""

from __future__ import annotations

from causaganha.decisoes.published import unpublished_fontes
from causaganha_mcp.agents_examples import AGENT_JOB_EXAMPLES
from causaganha_mcp.server import build_server


async def test_agents_examples_only_reference_registered_mcp_tools() -> None:
    """A rename/removal in build_server() must not silently stale an example question."""
    catalog = {tool.name for tool in await build_server().list_tools()}
    assert {example.tool for example in AGENT_JOB_EXAMPLES} <= catalog


def test_decisoes_buscar_example_never_names_an_unpublished_fonte() -> None:
    """The examples must not imply TCU is queryable before #1022 promotes it (#1036)."""
    (decisoes_example,) = (
        example for example in AGENT_JOB_EXAMPLES if example.tool == "decisoes_buscar"
    )
    for fonte in unpublished_fontes():
        assert fonte.lower() not in decisoes_example.pergunta.lower()


def test_every_public_job_has_exactly_one_example() -> None:
    """Freeze the example set at one per job — no job left without a copyable question."""
    tools = [example.tool for example in AGENT_JOB_EXAMPLES]
    assert len(tools) == len(set(tools)) == 4
