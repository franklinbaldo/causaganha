"""Normalização de número CNJ — módulo de domínio compartilhado (RFC 0014 M2).

Antes desta consolidação, a mesma regra existia em três lugares
independentes: `datajud.models` (Python), `scripts/reconcile_processos.py`
(Python) e `web/src/lib/processoCnj.ts` (TypeScript, cliente do dashboard).
Este módulo é agora a única implementação Python; `datajud.models` reexporta
estes nomes para não quebrar consumidores existentes, e
`scripts/reconcile_processos.py` importa daqui em vez de manter sua própria
cópia. A implementação TypeScript continua separada (runtime distinto,
DuckDB-WASM no navegador), mas segue a mesma regra — ver os comentários em
`processoCnj.ts`.
"""

from __future__ import annotations

import re


CNJ_LEN = 20


def so_digitos(value: str | None) -> str:
    """Remove todo caractere não numérico de *value*."""
    return re.sub(r"\D", "", value or "")


def normalizar_cnj(value: str | None) -> str:
    """Retorna o CNJ de 20 dígitos, ou '' quando *value* não é um CNJ válido."""
    digits = so_digitos(value)
    return digits if len(digits) == CNJ_LEN else ""


def formatar_cnj(value: str) -> str:
    """20 dígitos → NNNNNNN-DD.AAAA.J.TR.OOOO (máscara de exibição)."""
    digits = so_digitos(value)
    if len(digits) != CNJ_LEN:
        return value
    return (
        f"{digits[0:7]}-{digits[7:9]}.{digits[9:13]}."
        f"{digits[13:14]}.{digits[14:16]}.{digits[16:20]}"
    )
