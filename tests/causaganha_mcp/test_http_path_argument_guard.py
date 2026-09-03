"""HTTP transport must not accept caller-supplied local filesystem paths.

Next slice of #950's Segurança checklist ("não aceitar SQL, URL, caminho de
arquivo ou credencial arbitrários"): `tjro_juris_status`, `datajud_status`,
`djen_backup_status` and `stj_acordaos_status` all take a path-like argument
(`diretorio_dados`/`arquivo_manifesto`/`caminho_manifesto`) that flows
straight into `Path(...)` and is read from local disk. That is intentional
for local stdio/operator use (RFC 0013 Fase 3A), but a remote HTTP caller
should never be able to point the server at an arbitrary path on its own
disk. `OperationalLimitsMiddleware` already bounds *how long*/*how many*
remote tool calls run; this guards *what arguments* they may carry, on the
same transport-only boundary — stdio keeps accepting the argument.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext
from mcp.types import CallToolRequestParams

import causaganha_mcp.http_server as http_entry
from causaganha_mcp.http_server import PathArgumentGuardMiddleware


def _context(name: str, arguments: dict[str, Any] | None) -> MiddlewareContext:
    return MiddlewareContext(message=CallToolRequestParams(name=name, arguments=arguments))


async def _unexpected_call_next(_context: MiddlewareContext) -> str:
    msg = "call_next must not run once the guard rejects the argument"
    raise AssertionError(msg)


PATH_ARGUMENT_TOOLS = [
    ("tjro_juris_status", "diretorio_dados"),
    ("datajud_status", "diretorio_dados"),
    ("djen_backup_status", "arquivo_manifesto"),
    ("stj_acordaos_status", "caminho_manifesto"),
]


@pytest.mark.parametrize(("tool_name", "param"), PATH_ARGUMENT_TOOLS)
async def test_guard_rejects_explicit_path_argument(tool_name: str, param: str) -> None:
    guard = PathArgumentGuardMiddleware()
    context = _context(tool_name, {param: "/etc/passwd"})

    with pytest.raises(ToolError, match=param):
        await guard.on_call_tool(context, _unexpected_call_next)


@pytest.mark.parametrize(("tool_name", "param"), PATH_ARGUMENT_TOOLS)
async def test_guard_rejects_traversal_relative_to_default(tool_name: str, param: str) -> None:
    guard = PathArgumentGuardMiddleware()
    context = _context(tool_name, {param: "../../etc/passwd"})

    with pytest.raises(ToolError, match=param):
        await guard.on_call_tool(context, _unexpected_call_next)


@pytest.mark.parametrize(("tool_name", "param"), PATH_ARGUMENT_TOOLS)
async def test_guard_allows_call_without_explicit_path_argument(tool_name: str, param: str) -> None:
    guard = PathArgumentGuardMiddleware()
    context = _context(tool_name, {})

    async def call_next(_context: MiddlewareContext) -> str:
        return "ok"

    assert await guard.on_call_tool(context, call_next) == "ok"


@pytest.mark.parametrize(("tool_name", "param"), PATH_ARGUMENT_TOOLS)
async def test_guard_allows_call_with_no_arguments_at_all(tool_name: str, param: str) -> None:
    guard = PathArgumentGuardMiddleware()
    context = _context(tool_name, None)

    async def call_next(_context: MiddlewareContext) -> str:
        return "ok"

    assert await guard.on_call_tool(context, call_next) == "ok"


async def test_guard_leaves_tools_without_path_arguments_untouched() -> None:
    guard = PathArgumentGuardMiddleware()
    context = _context("processo_consultar", {"numero_processo": "12345"})

    async def call_next(_context: MiddlewareContext) -> str:
        return "ok"

    assert await guard.on_call_tool(context, call_next) == "ok"


def test_main_registers_path_argument_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    middleware: list[object] = []

    class FakeTool:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeServer:
        def add_middleware(self, item: object) -> None:
            middleware.append(item)

        async def list_tools(self) -> list[FakeTool]:
            return [FakeTool(name) for name in http_entry._READ_ONLY_TOOL_NAMES]

        def run(self, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(http_entry, "mcp", FakeServer())

    http_entry.main()

    assert any(isinstance(item, PathArgumentGuardMiddleware) for item in middleware)
