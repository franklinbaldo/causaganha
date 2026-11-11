"""Normalização de número CNJ — módulo de domínio compartilhado (RFC 0014 M2).

Antes desta consolidação, a mesma regra existia duplicada em `datajud.models`
e em `web/src/lib/processoCnj.ts` (TypeScript, cliente do dashboard). Este
módulo é agora a única implementação Python de uso geral; `datajud.models`
reexporta estes nomes para não quebrar consumidores existentes, e
`causaganha.processos.service` importa daqui. `scripts/reconcile_processos.py`
normaliza inline via `regexp_replace` em SQL (o CNJ nunca sai do DuckDB
durante a reconciliação), então não importa este módulo — mas segue a mesma
regra de 20 dígitos. A implementação TypeScript continua separada (runtime
distinto, DuckDB-WASM no navegador), também seguindo a mesma regra — ver os
comentários em `processoCnj.ts`.
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


def validar_digito_verificador(value: str | None) -> bool:
    """Valida o dígito verificador de um CNJ (Resolução CNJ 65/2008, art. 4º).

    O DV é o resto da divisão por 97 de sequencial+ano+segmento+tribunal+
    órgão (18 dígitos) seguido de "00", subtraído de 98. Um valor que não
    normaliza para 20 dígitos (ver `normalizar_cnj`) nunca é válido — este
    check é sobre o dígito verificador, não sobre a forma.
    """
    digits = so_digitos(value)
    if len(digits) != CNJ_LEN:
        return False
    corpo = digits[0:7] + digits[9:20]
    dv_informado = digits[7:9]
    resto = int(corpo + "00") % 97
    dv_calculado = 98 - resto
    return dv_informado == f"{dv_calculado:02d}"


def calcular_digito_verificador(
    numero_sequencial: int,
    ano: int,
    jtr: str,
    orgao: str,
) -> str:
    """Calcula o dígito verificador DD (2 dígitos) conforme Resolução CNJ 65/2008 (Módulo 97)."""
    corpo = f"{numero_sequencial:07d}{ano:04d}{jtr}{orgao}"
    resto = int(corpo + "00") % 97
    dv_calculado = 98 - resto
    return f"{dv_calculado:02d}"


def gerar_cnj(
    numero_sequencial: int,
    ano: int,
    jtr: str,
    orgao: str,
) -> str:
    """Gera o CNJ normalizado de 20 dígitos (NNNNNNNDDAAAAJTROOOO)."""
    dv = calcular_digito_verificador(numero_sequencial, ano, jtr, orgao)
    return f"{numero_sequencial:07d}{dv}{ano:04d}{jtr}{orgao}"


def extrapolar_sequencia_cnj(
    cnj_referencia: str,
    quantidade: int = 10,
    *,
    avancar: bool = True,
) -> list[str]:
    """Gera os próximos (ou anteriores) CNJs válidos a partir do sequencial de *cnj_referencia*.

    Extrai sequencial (7 dígitos), ano (4 dígitos), segmento+tribunal JTR (3 dígitos)
    e órgão judicante OOOO (4 dígitos), calculando o DV correto para cada novo número.
    """
    digits = normalizar_cnj(cnj_referencia)
    if not digits:
        msg = f"CNJ inválido para extrapolação: {cnj_referencia!r}"
        raise ValueError(msg)

    seq_atual = int(digits[0:7])
    ano = int(digits[9:13])
    jtr = digits[13:16]
    orgao = digits[16:20]

    resultado: list[str] = []
    step = 1 if avancar else -1

    for offset in range(1, quantidade + 1):
        novo_seq = seq_atual + (offset * step)
        if novo_seq <= 0 or novo_seq > 9_999_999:
            break
        resultado.append(gerar_cnj(novo_seq, ano, jtr, orgao))

    return resultado
