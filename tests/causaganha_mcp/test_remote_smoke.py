from __future__ import annotations

from dataclasses import dataclass

import pytest

from scripts.smoke_mcp_remote import _health_url, _mcp_url, _tool_name


@pytest.mark.parametrize(
    ("service_url", "expected"),
    [
        ("https://example.run.app", "https://example.run.app/mcp"),
        ("https://example.run.app/", "https://example.run.app/mcp"),
    ],
)
def test_mcp_url_is_stable(service_url: str, expected: str) -> None:
    assert _mcp_url(service_url) == expected


def test_health_url_is_service_root_health() -> None:
    assert _health_url("https://example.run.app/") == "https://example.run.app/health"


@dataclass
class _Tool:
    name: object


def test_tool_name_accepts_named_tool() -> None:
    assert _tool_name(_Tool(name="processo_consultar")) == "processo_consultar"


@pytest.mark.parametrize("name", [None, "", 123])
def test_tool_name_rejects_invalid_catalog_entry(name: object) -> None:
    with pytest.raises(RuntimeError, match="tool sem nome válido"):
        _tool_name(_Tool(name=name))
