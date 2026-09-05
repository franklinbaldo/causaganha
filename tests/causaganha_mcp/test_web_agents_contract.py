"""Contract between the public agents page and the canonical MCP catalog."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from causaganha.decisoes.published import unpublished_fontes
from causaganha_mcp.server import build_server


_AGENTS_PAGE = Path(__file__).parents[2] / "web" / "src" / "pages" / "agentes.astro"
_HOME_PAGE = Path(__file__).parents[2] / "web" / "src" / "pages" / "index.astro"

_EXPECTED_PUBLIC_JOBS = {
    "processo_consultar": "ARQUIVO",
    "publicacoes_buscar": "ARQUIVO",
    "processo_estado": "ESTADO",
    "decisoes_buscar": "TEOR",
}

# "todas" is the aggregate default, not a distinct source — the page lists
# only the individual fontes `decisoes_buscar` actually searches.
_AGGREGATE_FONTE = "todas"


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


class _DecisoesFonteParser(HTMLParser):
    """Collects data-mcp-fonte/data-mcp-status pairs inside the decisoes_buscar job card."""

    def __init__(self) -> None:
        super().__init__()
        self.fontes: set[str] = set()
        self.status_by_fonte: dict[str, str] = {}
        self._inside_decisoes_job = False
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "article" and attributes.get("data-mcp-tool") == "decisoes_buscar":
            self._inside_decisoes_job = True
            self._depth = 1
            return
        if self._inside_decisoes_job:
            self._depth += 1
            fonte = attributes.get("data-mcp-fonte")
            if fonte:
                self.fontes.add(fonte)
                status = attributes.get("data-mcp-status")
                if status:
                    self.status_by_fonte[fonte] = status

    def handle_endtag(self, tag: str) -> None:
        if not self._inside_decisoes_job:
            return
        self._depth -= 1
        if self._depth == 0:
            self._inside_decisoes_job = False


def _agents_page_decisoes_fontes() -> set[str]:
    parser = _DecisoesFonteParser()
    parser.feed(_AGENTS_PAGE.read_text(encoding="utf-8"))
    return parser.fontes


def _agents_page_decisoes_status_by_fonte() -> dict[str, str]:
    parser = _DecisoesFonteParser()
    parser.feed(_AGENTS_PAGE.read_text(encoding="utf-8"))
    return parser.status_by_fonte


async def _decisoes_buscar_fonte_enum() -> set[str]:
    tools = await build_server().list_tools()
    (decisoes_buscar,) = (tool for tool in tools if tool.name == "decisoes_buscar")
    enum_values = set(decisoes_buscar.parameters["properties"]["fonte"]["enum"])
    return enum_values - {_AGGREGATE_FONTE}


def test_agents_page_freezes_the_public_job_set() -> None:
    """Keep the public ARQUIVO/ESTADO/TEOR surface intentionally small."""
    assert _public_jobs() == _EXPECTED_PUBLIC_JOBS


async def test_agents_page_only_names_registered_mcp_tools() -> None:
    """A rename/removal in build_server() must not silently stale the website."""
    catalog = {tool.name for tool in await build_server().list_tools()}
    assert set(_public_jobs()) <= catalog


async def test_agents_page_lists_exactly_the_decisoes_buscar_fontes() -> None:
    """A fonte added/removed from decisoes_buscar must not silently drift from the site (#1011)."""
    assert _agents_page_decisoes_fontes() == await _decisoes_buscar_fonte_enum()


async def test_agents_page_marks_every_fonte_as_published_or_unpublished() -> None:
    """Recognized-but-unpublished fontes (#1036) must be explicit, never implied."""
    status_by_fonte = _agents_page_decisoes_status_by_fonte()
    assert set(status_by_fonte) == await _decisoes_buscar_fonte_enum()
    assert set(status_by_fonte.values()) <= {"published", "unpublished"}


def test_agents_page_unpublished_fontes_match_the_publication_authority() -> None:
    """The site must not claim TCU is queryable before #1022 promotes it (#1036).

    Uses the same authority the MCP tool consults, so promoting a fonte in
    ``causaganha.decisoes.published`` is the only edit needed — no second
    manually-maintained list on the site.
    """
    status_by_fonte = _agents_page_decisoes_status_by_fonte()
    site_unpublished = {
        fonte for fonte, status in status_by_fonte.items() if status == "unpublished"
    }
    assert site_unpublished == unpublished_fontes()


def test_home_agents_interface_links_to_the_public_agents_page() -> None:
    """Keep the MCP path inside the public product instead of bouncing to GitHub."""
    home = _HOME_PAGE.read_text(encoding="utf-8")
    assert "href={BASE + 'agentes'}" in home
    assert "Usar com um agente" in home
