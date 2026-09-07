"""Explicit public/operator MCP tool-catalog composition (#1244).

``causaganha_mcp`` has two different consumers with different trust levels:

- **public/product profile** (:func:`build_public_server`): what a remote,
  unauthenticated agent should see — the four canonical product jobs plus
  the aggregations that are genuinely product-facing and remote-safe
  (``datajud_facetas``, ``causaganha_status``). No tool in this profile
  accepts a local filesystem path.
- **operator/local profile** (:func:`build_operator_server`): everything
  in the public profile, plus the diagnostic status tools that read a
  local manifest and accept a caller-supplied directory/file path
  (``datajud_status``, ``djen_backup_status``, ``stj_acordaos_status``,
  ``tjro_juris_status``) — safe only for a local stdio operator.

This module only decides *which* ``register()`` calls run against a given
``FastMCP`` instance; it never reimplements a tool's business logic, so the
two profiles cannot drift into different behavior for the tools they share.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import (
    datajud,
    datajud_processo,
    decisoes,
    djen_backup,
    processo,
    publicacoes,
    status,
    stj_acordaos,
    tjro_juris,
)


_INSTRUCTIONS = (
    "Escolha a tool pelo trabalho que o usuário quer fazer:\n"
    "- Processo preservado e contexto histórico (ARQUIVO): `processo_consultar`.\n"
    "- Estado processual atual e movimentos oficiais (ESTADO): `processo_estado`.\n"
    "- Localizar publicações preservadas por processo, pessoa, OAB, texto, tribunal ou período: `publicacoes_buscar`.\n"
    "- Teor de decisão, acórdão, ementa ou tese (TEOR): `decisoes_buscar`.\n"
    "Tools de status/facetas são auxiliares para diagnóstico ou agregação. "
    "Use a cobertura, freshness, fonte e limitações retornadas por cada tool para interpretar ausência ou indisponibilidade."
)

PUBLIC_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "processo_consultar",
        "processo_estado",
        "publicacoes_buscar",
        "decisoes_buscar",
        "datajud_facetas",
        "causaganha_status",
    }
)

OPERATOR_ONLY_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "datajud_status",
        "djen_backup_status",
        "stj_acordaos_status",
        "tjro_juris_status",
    }
)


def build_public_server() -> FastMCP:
    """Construct the product-facing catalog: safe for a remote, unauthenticated caller.

    Registers only tools with no local-filesystem-path argument. This is
    the profile the ``/agentes`` page and any future remote HTTP endpoint
    (#950) should be checked against.
    """
    mcp = FastMCP(name="causaganha_mcp", instructions=_INSTRUCTIONS)
    processo.register(mcp)
    datajud_processo.register(mcp)
    publicacoes.register(mcp)
    decisoes.register(mcp)
    datajud.register_facetas(mcp)
    status.register(mcp)
    return mcp


def build_operator_server() -> FastMCP:
    """Construct the full catalog: public profile plus local operator diagnostics.

    Used by the stdio entrypoint (a single local, trusted client), where
    ``datajud_status(fonte='local', diretorio_dados=...)`` and its three
    manifest-path siblings remain legitimate.
    """
    mcp = build_public_server()
    datajud.register_status(mcp)
    djen_backup.register(mcp)
    stj_acordaos.register(mcp)
    tjro_juris.register(mcp)
    return mcp
