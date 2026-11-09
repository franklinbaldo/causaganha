"""Extrator e Validador de Números Únicos de Processos do CNJ (Resolução nº 65/2008)."""

from __future__ import annotations

import re

from causaganha.decisoes.ner.models import CnjValue, EntityRole, EntityType, JudicialMention

# Regex canônica para número CNJ (com e sem pontuação)
REGEX_CNJ = re.compile(
    r"\b(?P<seq>\d{7})[-. ]?(?P<dv>\d{2})[-. ]?(?P<ano>\d{4})[-. ]?(?P<ramo>\d)[-. ]?(?P<trib>\d{2})[-. ]?(?P<origem>\d{4})\b"
)


def validate_cnj_modulo_97(seq: str, dv: str, ano: str, ramo: str, trib: str, origem: str) -> bool:
    """Valida o dígito verificador do CNJ usando o algoritmo Módulo 97 Base 10 (Resolução CNJ 65/2008).

    Fórmula:
    R1 = int(sequencial) % 97
    R2 = int(f"{R1:02d}{ano}{ramo}{trib}") % 97
    R3 = int(f"{R2:02d}{origem}00") % 97
    dv_esperado = 98 - R3
    """
    try:
        r1 = int(seq) % 97
        r2 = int(f"{r1:02d}{ano}{ramo}{trib}") % 97
        r3 = int(f"{r2:02d}{origem}00") % 97
        expected_dv = 98 - r3
        return expected_dv == int(dv)
    except (ValueError, TypeError):
        return False


class CnjExtractor:
    """Extrator determinístico especializado em números de processo CNJ."""

    def extract(self, text: str, section: str = "CABECALHO") -> list[JudicialMention]:
        mentions: list[JudicialMention] = []

        is_first_cnj = True
        for m in REGEX_CNJ.finditer(text):
            seq = m.group("seq")
            dv = m.group("dv")
            ano = m.group("ano")
            ramo = m.group("ramo")
            trib = m.group("trib")
            origem = m.group("origem")

            formatted = f"{seq}-{dv}.{ano}.{ramo}.{trib}.{origem}"
            is_valid = validate_cnj_modulo_97(seq, dv, ano, ramo, trib, origem)

            ctx_start = max(0, m.start() - 80)
            ctx_before = text[ctx_start : m.start()].lower()

            # Papel Semântico: O primeiro CNJ no cabeçalho/início é o processo principal;
            # processos subsequentes são citados ou paradigmas
            if is_first_cnj and (section in {"CABECALHO"} or m.start() < 350):
                role = EntityRole.PROCESSO_PRINCIPAL
                evidence = "Primeiro número CNJ localizado no cabeçalho / início do ato"
                is_first_cnj = False
            elif "paradigma" in ctx_before or "precedente" in ctx_before or "tema" in ctx_before:
                role = EntityRole.PROCESSO_PARADIGMA
                evidence = f"Citado como paradigma / precedente na seção {section}"
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
