"""Extrator e Validador de Números Únicos de Processos do CNJ (Resolução nº 65/2008)."""

from __future__ import annotations

import re
from typing import Any

from causaganha.decisoes.ner.models import CnjValue, EntityRole, EntityType, JudicialMention
from causaganha.processos.cnj import (
    normalizar_cnj,
    validar_digito_verificador,
)

# Regex canônica para número CNJ (com e sem pontuação)
REGEX_CNJ = re.compile(
    r"\b(?P<seq>\d{7})[-. ]?(?P<dv>\d{2})[-. ]?(?P<ano>\d{4})[-. ]?(?P<ramo>\d)[-. ]?(?P<trib>\d{2})[-. ]?(?P<origem>\d{4})\b"
)


def validate_cnj_modulo_97(seq: str, dv: str, ano: str, ramo: str, trib: str, origem: str) -> bool:
    """Valida o dígito verificador do CNJ usando o algoritmo Módulo 97 Base 10 (Resolução CNJ 65/2008)."""
    digits = f"{seq}{dv}{ano}{ramo}{trib}{origem}"
    return validar_digito_verificador(digits)


class CnjExtractor:
    """Extrator determinístico especializado em números de processo CNJ."""

    def extract(
        self,
        text: str,
        section: str = "CABECALHO",
        metadata: dict[str, Any] | None = None,
    ) -> list[JudicialMention]:
        meta = metadata or {}
        mentions: list[JudicialMention] = []

        # 1. Recupera o CNJ oficial dos metadados do DJEN (Fonte de Verdade Canônica)
        djen_raw = (
            meta.get("numero_processo")
            or meta.get("numero_processo_mascara")
            or meta.get("cnj")
            or meta.get("process_number")
        )
        djen_clean = normalizar_cnj(str(djen_raw)) if djen_raw else ""

        is_first_cnj = True
        for m in REGEX_CNJ.finditer(text):
            seq = m.group("seq")
            dv = m.group("dv")
            ano = m.group("ano")
            ramo = m.group("ramo")
            trib = m.group("trib")
            origem = m.group("origem")

            formatted = f"{seq}-{dv}.{ano}.{ramo}.{trib}.{origem}"
            clean_digits = f"{seq}{dv}{ano}{ramo}{trib}{origem}"
            is_valid = validar_digito_verificador(clean_digits)

            ctx_start = max(0, m.start() - 80)
            ctx_before = text[ctx_start : m.start()].lower()

            # Papel Semântico: O processo principal DEVE vir dos metadados do DJEN.
            if djen_clean:
                if clean_digits == djen_clean:
                    role = EntityRole.PROCESSO_PRINCIPAL
                    evidence = (
                        "Menção textual idêntica ao numero_processo oficial dos metadados do DJEN"
                    )
                elif (
                    "paradigma" in ctx_before or "precedente" in ctx_before or "tema" in ctx_before
                ):
                    role = EntityRole.PROCESSO_PARADIGMA
                    evidence = f"Citado como paradigma / precedente na seção {section}"
                else:
                    role = EntityRole.PROCESSO_CITADO
                    evidence = f"Processo citado na seção {section} (distinto do metadado oficial do DJEN {djen_clean})"
            else:
                # Se não há metadados do DJEN disponíveis:
                if "paradigma" in ctx_before or "precedente" in ctx_before or "tema" in ctx_before:
                    role = EntityRole.PROCESSO_PARADIGMA
                    evidence = f"Citado como paradigma / precedente na seção {section}"
                elif is_first_cnj and (section in {"CABECALHO"} or m.start() < 350):
                    role = EntityRole.PROCESSO_PRINCIPAL
                    evidence = (
                        "Inferido provisoriamente do cabeçalho por ausência de metadados do DJEN"
                    )
                    is_first_cnj = False
                else:
                    role = EntityRole.PROCESSO_CITADO
                    evidence = f"Processo citado na seção {section}"

            cnj_val = CnjValue(
                numero_formatado=formatted,
                sequencial=seq,
                digito_verificador=dv,
                ano=int(ano),
                ramo_justica=int(ramo),
                tribunal=int(trib),
                origem=origem,
                is_valid_mod97=is_valid,
            )

            # Se o módulo 97 bateu, confiança é 1.0 (certeza matemática absoluta);
            # se não bateu, confiança é 0.60 (pode ser erro de digitação do cartório)
            confidence = 1.0 if is_valid else 0.60

            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.CNJ,
                    normalized_value=cnj_val,
                    role=role,
                    confidence=confidence,
                    evidence=evidence,
                )
            )

        return mentions
