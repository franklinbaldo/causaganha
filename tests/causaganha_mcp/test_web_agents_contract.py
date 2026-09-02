"""Contract between the public agents page and the canonical MCP catalog."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from causaganha_mcp.server import build_server


_AGENTS_PAGE = Path(__file__).parents[2] / "web" / "src" / "pages" / "agentes.astro"

_EXPECTED_PUBLIC_JOBS = {
    "processo_consultar": "ARQUIVO",
    "publicacoes_buscar": "ARQUIVO",
    "processo_estado": "ESTADO",
    "decisoes_buscar": "TEOR",
}


class _PublicJobParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.jobs: dict[str, str] = {}
        self._tool: str | None = None
        self._capture_job_code = False
        self._job_code_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article" and attributes.get("data-mcp-tool"):
            self._tool = attributes["data-mcp-tool"]
            self._job_code_parts = []
            return

        classes = (attributes.get("class") or "").split()
        if self._tool and tag == "span" and "job-code" in classes:
            self._capture_job_code = True

    def handle_data(self, data: str) -> None:
        if self._capture_job_code:
            self._job_code_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture_job_code:
            self._capture_job_code = False
            return

        if tag == "article" and self._tool:
            job_code = " ".join("".join(self._job_code_parts).split())
            self.jobs[self._tool] = job_code
            self._tool = None
            self._job_code_parts = []


def _public_jobs() -> dict[str, str]:
    parser = _PublicJobParser()
    parser.feed(_AGENTS_PAGE.read_text(encoding="utf-8"))
    return parser.jobs


def test_agents_page_freezes_the_public_job_set() -> None:
    """Keep the public ARQUIVO/ESTADO/TEOR surface intentionally small."""
    assert _public_jobs() == _EXPECTED_PUBLIC_JOBS


async def test_agents_page_only_names_registered_mcp_tools() -> None:
    """A rename/removal in build_server() must not silently stale the website."""
    catalog = {tool.name for tool in await build_server().list_tools()}
    assert set(_public_jobs()) <= catalog
