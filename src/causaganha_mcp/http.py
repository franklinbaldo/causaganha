"""HTTP entry point for the same read-only CausaGanha MCP facade used by stdio."""

from __future__ import annotations

import os
from dataclasses import dataclass

from causaganha_mcp.server import mcp


_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000
_DEFAULT_PATH = "/mcp"


@dataclass(frozen=True, slots=True)
class HttpSettings:
    """Network settings for the remote MCP transport.

    The defaults are deliberately loopback-safe for local use. A container or
    hosted service must opt in to an external bind, normally with
    ``CAUSAGANHA_MCP_HOST=0.0.0.0``.
    """

    host: str = _DEFAULT_HOST
    port: int = _DEFAULT_PORT
    path: str = _DEFAULT_PATH

    @classmethod
    def from_env(cls) -> HttpSettings:
        """Load transport-only settings without introducing secrets."""
        host = os.getenv("CAUSAGANHA_MCP_HOST", _DEFAULT_HOST).strip() or _DEFAULT_HOST
        port_text = os.getenv("CAUSAGANHA_MCP_PORT", str(_DEFAULT_PORT)).strip()
        path = os.getenv("CAUSAGANHA_MCP_PATH", _DEFAULT_PATH).strip() or _DEFAULT_PATH

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

        return cls(host=host, port=port, path=path)


def main() -> None:
    """Serve the canonical CausaGanha MCP catalog over Streamable HTTP."""
    settings = HttpSettings.from_env()
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
        path=settings.path,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
