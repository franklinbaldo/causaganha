"""Real stdio-transport regression test (RFC 0013 Fase 3A review).

`test_tool_behavior.py` calls `tool.fn(...)` directly — it captures the
correct return *value* but never touches the actual JSON-RPC transport, so
it cannot catch a bug where a tool's dependencies write to stdout: in MCP
stdio transport, stdout is exclusively the JSON-RPC channel, and structlog's
default `PrintLogger` writes there unless explicitly configured otherwise.
`ManifestSTJ.load()` and `SyncManifest.load_from_disk()` both call
`log.info(...)` when the manifest file actually has entries to load — so
this only reproduces with a *populated* manifest, which is exactly the
scenario exercised here.

This spawns the real server as a subprocess over real stdio
(`PythonStdioTransport`) and drives it with `fastmcp.Client`, the same way
a real MCP host would. `caplog` on the `mcp.client.stdio` logger is the
deterministic signal: a corrupted JSON-RPC stream makes the client log
"Failed to parse JSONRPC message from server" via `logger.exception(...)`
(see `mcp/client/stdio/__init__.py`) — checking for that beats asserting on
the call's return value, which can still come back correct by chance
depending on how the stray line lands relative to message boundaries.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

from djen_backup.manifest import HEADER
from stj_acordaos.manifest import ManifestSTJ


if TYPE_CHECKING:
    import pytest


_MAIN_SCRIPT = Path(__file__).parents[2] / "src" / "causaganha_mcp" / "__main__.py"


async def test_stj_acordaos_status_over_real_stdio_does_not_corrupt_json_rpc(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    manifest_path = tmp_path / "stj-manifest.csv"
    manifest = ManifestSTJ(manifest_path)
    manifest.upsert("20260531.json.json", "json", "2026-05-31", "uploaded", 12)
    manifest.save()  # triggers ManifestSTJ.load()'s log.info() on the next load

    transport = PythonStdioTransport(script_path=_MAIN_SCRIPT, python_cmd=sys.executable)
    with caplog.at_level(logging.WARNING, logger="mcp.client.stdio"):
        async with Client(transport) as client:
            result = await client.call_tool(
                "stj_acordaos_status", {"manifest_path": str(manifest_path)}
            )

    assert result.data.count == 1
    assert result.data.uploaded == 1
    assert not any("Failed to parse" in r.message for r in caplog.records), caplog.text


async def test_djen_backup_status_over_real_stdio_does_not_corrupt_json_rpc(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    manifest_file = tmp_path / "sync-manifest.csv"
    manifest_file.write_text(
        f"{HEADER}\nTJRO,2026-01-01,uploaded,available,200,2026-01-01T00:00:00\n",
        encoding="utf-8",
    )  # triggers SyncManifest.load_from_disk()'s log.info()

    transport = PythonStdioTransport(script_path=_MAIN_SCRIPT, python_cmd=sys.executable)
    with caplog.at_level(logging.WARNING, logger="mcp.client.stdio"):
        async with Client(transport) as client:
            result = await client.call_tool(
                "djen_backup_status", {"manifest_file": str(manifest_file)}
            )

    assert result.data.total == 1
    assert result.data.uploaded == 1
    assert not any("Failed to parse" in r.message for r in caplog.records), caplog.text
