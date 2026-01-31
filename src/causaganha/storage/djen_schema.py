"""Ibis schemas — 1:1 mapping of djen.yml (OpenAPI 3.0.1).

Each ``ibis.Schema`` corresponds to one entity defined in the DJEN API
swagger.  Field names are preserved **exactly** as returned by the API
(mixed camelCase / snake_case).

Swagger type mapping
--------------------
=============  ==========
Swagger type   Ibis type
=============  ==========
string         string
number         int64
integer        int64
boolean        boolean
=============  ==========
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import ibis


if TYPE_CHECKING:
    from ibis.expr.schema import Schema


# ── GET /api/v1/comunicacao  →  response.items[] ────────────────────────

comunicacao: Schema = ibis.schema(
    {
        "id": "int64",  # Id da comunicação
        "data_disponibilizacao": "string",  # yyyy-mm-dd
        "siglaTribunal": "string",
        "tipoComunicacao": "string",  # Citação, Intimação, Edital, …
        "nomeOrgao": "string",
        "texto": "string",  # Teor da comunicação
        "numero_processo": "string",
        "meio": "string",  # D=Diário, E=Edital
        "link": "string",  # URL inteiro teor
        "tipoDocumento": "string",
        "nomeClasse": "string",  # Classe do processo
        "codigoClasse": "string",
        "numeroComunicacao": "int64",  # Número de identificação
        "ativo": "boolean",
        "hash": "string",
        "datadisponibilizacao": "string",  # Alternate (no underscore)
        "meiocompleto": "string",
        "numeroprocessocommascara": "string",
    },
)


# ── comunicacao.destinatarios[] ──────────────────────────────────────────

destinatario: Schema = ibis.schema(
    {
        "nome": "string",
        "polo": "string",  # A=Ativo, P=Passivo, T=Terceiro, D=Outros
        "comunicacao_id": "int64",
        "cpf_cnpj": "string",  # Present in POST request/response
    },
)


# ── comunicacao.destinatarioadvogados[] ──────────────────────────────────

destinatario_advogado: Schema = ibis.schema(
    {
        "id": "int64",
        "comunicacao_id": "int64",
        "advogado_id": "int64",
        "created_at": "string",
        "updated_at": "string",
    },
)


# ── comunicacao.destinatarioadvogados[].advogado ─────────────────────────

advogado: Schema = ibis.schema(
    {
        "id": "int64",  # required
        "nome": "string",  # required
        "numero_oab": "string",  # required
        "uf_oab": "string",  # required
        "tipo_inscricao": "string",  # POST response only
        "email": "string",  # POST response only
    },
)


# ── GET /api/v1/comunicacao/tribunal  →  response[] ─────────────────────

tribunal: Schema = ibis.schema(
    {
        "id": "int64",
        "nome": "string",  # Nome completo do Tribunal
        "sigla": "string",  # Sigla do Tribunal
        "jurisdicao": "string",
        "endereco": "string",
        "telefone": "string",
    },
)


# ── GET /api/v1/caderno/{sigla_tribunal}/{data}/{meio}  →  response ─────

caderno: Schema = ibis.schema(
    {
        "tribunal": "string",  # Nome completo
        "sigla_tribunal": "string",
        "meio": "string",  # D or E
        "status": "string",  # Não Processado / Em processamento / Processado / …
        "versao": "string",
        "data": "string",  # yyyy-mm-dd
        "total_comunicacoes": "int64",
        "numero_paginas": "int64",  # Files inside ZIP
        "hash": "string",  # SHA-256
        "url": "string",  # Temporary download URL (5 min)
    },
)


# ── Lookup table ─────────────────────────────────────────────────────────

SCHEMAS: dict[str, Schema] = {
    "comunicacao": comunicacao,
    "destinatario": destinatario,
    "destinatario_advogado": destinatario_advogado,
    "advogado": advogado,
    "tribunal": tribunal,
    "caderno": caderno,
}
