"""Contrato executável da configuração stdio publicada em ``/agentes``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from djen_backup.manifest import HEADER


if TYPE_CHECKING:
    import pytest


_REPO_ROOT = Path(__file__).parents[2]
_AGENT_PAGE = _REPO_ROOT / "web" / "src" / "pages" / "agentes.astro"
_CHECKOUT_PLACEHOLDER = "/caminho/para/causaganha"
_LOCAL_CONFIG_RE = re.compile(r"const localConfig = `(?P<config>.*?)`;", re.DOTALL)


def _published_server_config() -> dict[str, object]:
    source = _AGENT_PAGE.read_text(encoding="utf-8")
    match = _LOCAL_CONFIG_RE.search(source)
    assert match is not None, "agentes.astro precisa publicar localConfig"
    config = json.loads(match.group("config"))
    return config["mcpServers"]["causaganha"]


async def test_published_stdio_recipe_works_from_outside_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receita copiável deve funcionar sem herdar o cwd do checkout."""
    manifest_file = tmp_path / "sync-manifest.csv"
    manifest_file.write_text(
        f"{HEADER}\nTJRO,2026-01-01,uploaded,available,200,2026-01-01T00:00:00\n",
        encoding="utf-8",
    )

    server = _published_server_config()
    command = server["command"]
    args = [str(_REPO_ROOT) if arg == _CHECKOUT_PLACEHOLDER else arg for arg in server["args"]]

    assert command == "uv"
    assert _CHECKOUT_PLACEHOLDER in server["args"]

    monkeypatch.chdir(tmp_path)
    params = StdioServerParameters(command=command, args=args)
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(
                "djen_backup_status", {"arquivo_manifesto": str(manifest_file)}
            )

    assert "djen_backup_status" in {tool.name for tool in tools.tools}
    assert result.isError is not True
