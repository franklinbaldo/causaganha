"""HTTP entry point for the public, remote-safe CausaGanha MCP profile."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from anyio import CapacityLimiter, WouldBlock, fail_after
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.responses import JSONResponse

from causaganha_mcp import __version__
from causaganha_mcp.profiles import build_public_server


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request


_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000
_DEFAULT_PATH = "/mcp"
_DEFAULT_TOOL_TIMEOUT_SECONDS = 45.0
_DEFAULT_MAX_CONCURRENCY = 4
_COMMIT_ENV_VAR = "CAUSAGANHA_MCP_COMMIT"
_UNKNOWN_COMMIT = "unknown"

# HTTP is structurally bound to the remote-safe catalog. Local/operator tools
# never get registered here, so the transport does not need a second blacklist
# or argument guard to compensate for an over-broad server composition.
mcp = build_public_server()


@dataclass(frozen=True, slots=True)
class HttpSettings:
    """Network and operational settings for the remote MCP transport.

    The defaults are deliberately loopback-safe for local use. A container or
    hosted service must opt in to an external bind, normally with
    ``CAUSAGANHA_MCP_HOST=0.0.0.0``.
    """

    host: str = _DEFAULT_HOST
    port: int = _DEFAULT_PORT
    path: str = _DEFAULT_PATH
    tool_timeout_seconds: float = _DEFAULT_TOOL_TIMEOUT_SECONDS
    max_concurrency: int = _DEFAULT_MAX_CONCURRENCY

    @classmethod
    def from_env(cls) -> HttpSettings:
        """Load transport-only settings without introducing secrets."""
        host = os.getenv("CAUSAGANHA_MCP_HOST", _DEFAULT_HOST).strip() or _DEFAULT_HOST
        port_text = os.getenv("CAUSAGANHA_MCP_PORT", str(_DEFAULT_PORT)).strip()
        path = os.getenv("CAUSAGANHA_MCP_PATH", _DEFAULT_PATH).strip() or _DEFAULT_PATH
        timeout_text = os.getenv(
            "CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS",
            str(_DEFAULT_TOOL_TIMEOUT_SECONDS),
        ).strip()
        concurrency_text = os.getenv(
            "CAUSAGANHA_MCP_MAX_CONCURRENCY",
            str(_DEFAULT_MAX_CONCURRENCY),
        ).strip()

        try:
            port = int(port_text)
        except ValueError as exc:
            msg = "CAUSAGANHA_MCP_PORT deve ser um inteiro entre 1 e 65535."
            raise ValueError(msg) from exc
        if not 1 <= port <= 65535:
            msg = "CAUSAGANHA_MCP_PORT deve estar entre 1 e 65535."
            raise ValueError(msg)
        if not path.startswith("/"):
            msg = "CAUSAGANHA_MCP_PATH deve começar com '/'."
            raise ValueError(msg)

        try:
            tool_timeout_seconds = float(timeout_text)
        except ValueError as exc:
            msg = "CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS deve ser um número positivo."
            raise ValueError(msg) from exc
        if tool_timeout_seconds <= 0:
            msg = "CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS deve ser maior que zero."
            raise ValueError(msg)

        try:
            max_concurrency = int(concurrency_text)
        except ValueError as exc:
            msg = "CAUSAGANHA_MCP_MAX_CONCURRENCY deve ser um inteiro positivo."
            raise ValueError(msg) from exc
        if max_concurrency <= 0:
            msg = "CAUSAGANHA_MCP_MAX_CONCURRENCY deve ser maior que zero."
            raise ValueError(msg)

        return cls(
            host=host,
            port=port,
            path=path,
            tool_timeout_seconds=tool_timeout_seconds,
            max_concurrency=max_concurrency,
        )


class OperationalLimitsMiddleware(Middleware):
    """Bound remote tool work without changing tool semantics or health checks."""

    def __init__(self, *, timeout_seconds: float, max_concurrency: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_concurrency = max_concurrency
        self._limiter = CapacityLimiter(max_concurrency)

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:
        """Reject saturation explicitly and classify execution timeouts as errors."""
        try:
            self._limiter.acquire_nowait()
        except WouldBlock as exc:
            msg = (
                "CausaGanha MCP está temporariamente saturado; tente novamente mais tarde. "
                "Nenhuma ausência de dado foi inferida."
            )
            raise ToolError(msg) from exc

        try:
            try:
                with fail_after(self.timeout_seconds):
                    return await call_next(context)
            except TimeoutError as exc:
                msg = (
                    "A consulta excedeu o limite operacional de "
                    f"{self.timeout_seconds:g}s; tente novamente. "
                    "Timeout não significa ausência de dado."
                )
                raise ToolError(msg) from exc
        finally:
            self._limiter.release()


def _deployment_commit() -> str:
    """Read the deployed commit from the environment, without shelling out to git."""
    return os.getenv(_COMMIT_ENV_VAR, "").strip() or _UNKNOWN_COMMIT


@mcp.custom_route("/health", methods=["GET"])
async def _health(request: Request) -> JSONResponse:
    """Prove the public MCP catalog is up and report version/commit, with no upstream calls."""
    tools = await mcp.list_tools()
    return JSONResponse(
        {
            "status": "ok",
            "version": __version__,
            "commit": _deployment_commit(),
            "tools": len(tools),
        }
    )


def main() -> None:
    """Serve the public CausaGanha MCP profile over Streamable HTTP."""
    settings = HttpSettings.from_env()
    mcp.add_middleware(
        OperationalLimitsMiddleware(
            timeout_seconds=settings.tool_timeout_seconds,
            max_concurrency=settings.max_concurrency,
        )
    )
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
        path=settings.path,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
