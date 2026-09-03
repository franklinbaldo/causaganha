"""HTTP transport must refuse to start if a non-reviewed tool is exposed.

Closes the remaining #950 Segurança checklist gap: "nenhuma operação
mutável é exposta" was previously an unenforced assumption — nothing
stopped a future tool registered in `causaganha_mcp.server.build_server()`
from being silently served over the remote HTTP transport. This locks the
set of tools the HTTP entrypoint will ever serve to a reviewed allowlist,
so any addition to the catalog requires deliberately updating
`_READ_ONLY_TOOL_NAMES` after a security review — the same fail-closed
pattern `PathArgumentGuardMiddleware` already established for path
arguments.
"""

from __future__ import annotations

import pytest

import causaganha_mcp.http_server as http_entry
from causaganha_mcp.server import build_server


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeServer:
    def __init__(self, tool_names: list[str]) -> None:
        self._tool_names = tool_names
        self.middleware: list[object] = []
        self.ran = False

    def add_middleware(self, item: object) -> None:
        self.middleware.append(item)

    async def list_tools(self) -> list[_FakeTool]:
        return [_FakeTool(name) for name in self._tool_names]

    def run(self, **_kwargs: object) -> None:
        self.ran = True


async def test_read_only_allowlist_matches_canonical_catalog() -> None:
    """The reviewed allowlist must track build_server() exactly — no silent drift."""
    tools = await build_server().list_tools()
    catalog_names = {tool.name for tool in tools}

    assert catalog_names == http_entry._READ_ONLY_TOOL_NAMES


def test_main_starts_when_catalog_matches_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeServer(sorted(http_entry._READ_ONLY_TOOL_NAMES))
    monkeypatch.setattr(http_entry, "mcp", fake)

    http_entry.main()

    assert fake.ran is True


def test_main_refuses_to_start_when_unreviewed_tool_is_exposed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeServer([*sorted(http_entry._READ_ONLY_TOOL_NAMES), "backfill_upload"])
    monkeypatch.setattr(http_entry, "mcp", fake)

    with pytest.raises(RuntimeError, match="backfill_upload"):
        http_entry.main()

    assert fake.ran is False
