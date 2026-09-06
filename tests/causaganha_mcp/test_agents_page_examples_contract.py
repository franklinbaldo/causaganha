"""Contract for the copyable example questions on the public agents page (#1217).

`test_web_agents_contract.py` already gates the page's four job/role/fonte
labels against `build_server()`'s live catalog and the published-fontes
authority. This file extends the same pattern to the per-job example
question each card must now show: `agents_examples.AGENT_JOB_EXAMPLES` is the
single authority for the wording, and the page must reproduce it verbatim.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from causaganha.decisoes.published import unpublished_fontes
from causaganha_mcp.agents_examples import AGENT_JOB_EXAMPLES
from causaganha_mcp.server import build_server


_ROOT = Path(__file__).parents[2]
_AGENTS_PAGE = _ROOT / "web" / "src" / "pages" / "agentes.astro"


class _ExampleQuestionParser(HTMLParser):
    """Collect the example `question` shown inside each job's `<article>`."""

    def __init__(self) -> None:
        super().__init__()
        self.question_by_tool: dict[str, str] = {}
        self._current_tool: str | None = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article" and attributes.get("data-mcp-tool"):
            self._current_tool = attributes["data-mcp-tool"]
            self._depth = 1
            return
        if self._current_tool is not None:
            self._depth += 1
            if tag.lower() == "copyquestionexample" and attributes.get("question"):
                self.question_by_tool[self._current_tool] = attributes["question"]

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self._current_tool is not None:
            self._depth -= 1

    def handle_endtag(self, tag: str) -> None:
        if self._current_tool is None:
            return
        self._depth -= 1
        if self._depth == 0:
            self._current_tool = None


def _questions_by_tool() -> dict[str, str]:
    parser = _ExampleQuestionParser()
    parser.feed(_AGENTS_PAGE.read_text(encoding="utf-8"))
    return parser.question_by_tool


def test_agents_page_shows_the_canonical_example_for_every_public_job() -> None:
    """The page must show, verbatim, this module's wording — no second copy to drift (#1217)."""
    canonical = {example.tool: example.pergunta for example in AGENT_JOB_EXAMPLES}
    assert _questions_by_tool() == canonical


async def test_agents_page_examples_only_reference_registered_mcp_tools() -> None:
    """A rename/removal in build_server() must not silently stale an example question."""
    catalog = {tool.name for tool in await build_server().list_tools()}
    assert {example.tool for example in AGENT_JOB_EXAMPLES} <= catalog


def test_decisoes_buscar_example_never_names_an_unpublished_fonte() -> None:
    """The site must not imply TCU is queryable before #1022 promotes it (#1036)."""
    (decisoes_example,) = (
        example for example in AGENT_JOB_EXAMPLES if example.tool == "decisoes_buscar"
    )
    for fonte in unpublished_fontes():
        assert fonte.lower() not in decisoes_example.pergunta.lower()


def test_every_public_job_has_exactly_one_example() -> None:
    """Freeze the example set at one per job — no job left without a copyable question."""
    tools = [example.tool for example in AGENT_JOB_EXAMPLES]
    assert len(tools) == len(set(tools)) == 4
