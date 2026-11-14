"""Contrato executável da configuração stdio publicada no README."""

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
_README = _REPO_ROOT / "README.md"
_CHECKOUT_PLACEHOLDER = "/caminho/para/causaganha"
_JSON_BLOCK_RE = re.compile(r"```json\n(?P<config>\{.*?\})\n```", re.DOTALL)


def _published_server_config() -> dict[str, object]:
    source = _README.read_text(encoding="utf-8")
    configs = [json.loads(match.group("config")) for match in _JSON_BLOCK_RE.finditer(source)]
    published = next((config for config in configs if "mcpServers" in config), None)
    assert published is not None, "README.md precisa publicar a configuração mcpServers"
    return published["mcpServers"]["causaganha"]


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
