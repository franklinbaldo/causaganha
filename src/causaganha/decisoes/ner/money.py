"""Extrator e Normalizador de Valores Monetários e Sucumbenciais em Decisões Judiciais."""

from __future__ import annotations

import re

from causaganha.decisoes.ner.models import EntityRole, EntityType, JudicialMention, MoneyValue

# Regex para valores em Reais (R$)
REGEX_MONEY_BRL = re.compile(
    r"\bR\$\s*(?P<val>[\d]{1,3}(?:\.[\d]{3})*(?:,[\d]{2})?|\d+(?:,[\d]{2})?)\b"
)

# Regex para percentuais de honorários e juros (ex: 10%, 15%, 20%)
REGEX_PERCENT = re.compile(r"\b(?P<val>\d{1,2}(?:,\d+)?)\s*%(?!\w)")


def parse_brazilian_currency(val_str: str) -> float:
    """Converte valor monetário formatado no padrão brasileiro para float."""
    # Remove separadores de milhar (ponto) e troca vírgula decimal por ponto
    clean = val_str.replace(".", "").replace(",", ".")
    return float(clean)


class MonetaryValueExtractor:
    """Extrator especializado em quantias financeiras, condenações e honorários."""

    def extract(self, text: str, section: str = "DISPOSITIVO") -> list[JudicialMention]:
        mentions: list[JudicialMention] = []

        # 1. Extração de Valores em Moeda (R$)
        for m in REGEX_MONEY_BRL.finditer(text):
            raw_val = m.group("val")
            try:
                amount = parse_brazilian_currency(raw_val)
            except ValueError:
                continue

            # Contexto vizinho (100 caracteres antes)
            # Contexto da oração/período imediato (até a quebra de linha ou pontuação anterior)
            ctx_start = max(0, m.start() - 120)
            raw_before = text[ctx_start : m.start()]
            last_break = max(raw_before.rfind("\n"), raw_before.rfind(". "), raw_before.rfind("; "))
            if last_break != -1:
                context_before = raw_before[last_break:].lower()
            else:
                context_before = raw_before.lower()

            ctx_end = min(len(text), m.end() + 80)
            raw_after = text[m.end() : ctx_end]
            next_breaks = [p for p in (raw_after.find("\n"), raw_after.find(". ")) if p != -1]
            context_after = (
                raw_after[: min(next_breaks)].lower() if next_breaks else raw_after.lower()
            )
            immediate_sentence = context_before + " " + context_after

            # Resolução de Papel Semântico
            qualifier = None
            if re.search(r"\b(?:valor\s+da\s+causa|atribui-se)\b", immediate_sentence):
                role = EntityRole.VALOR_DA_CAUSA
                qualifier = "valor_da_causa"
                evidence = "Indicado como valor atribuído à causa"
            elif re.search(
                r"\b(?:conden|pagamento\s+d[eo]|indeniza[cç][aã]o|danos?\s+morais?)\b",
                immediate_sentence,
            ):
                role = EntityRole.VALOR_CONDENACAO_PRINCIPAL
                qualifier = "condenacao_principal"
                evidence = "Fixado como obrigação de pagar / condenação de mérito"
            elif (
                re.search(r"\bhonor[aá]rios\b", immediate_sentence)
                or section == "HONORARIOS_CUSTAS"
            ):
                role = EntityRole.VALOR_HONORARIOS
                qualifier = "honorarios_advocaticios"
                evidence = "Associado a honorários sucumbenciais"
            elif re.search(r"\b(?:multa|astreinte)\b", immediate_sentence):
                role = EntityRole.VALOR_ASTREINTES_MULTA
                qualifier = "multa_diaria_astreintes"
                evidence = "Cominado como multa coercitiva"
            elif section == "CABECALHO":
                role = EntityRole.VALOR_DA_CAUSA
                qualifier = "valor_da_causa"
                evidence = "Valor citado no cabeçalho"
            elif section == "DISPOSITIVO":
                role = EntityRole.VALOR_CONDENACAO_PRINCIPAL
                qualifier = "dispositivo_generico"
                evidence = "Quantia fixada na seção Dispositivo"
            else:
                role = EntityRole.VALOR_MENCIONADO
                evidence = f"Quantia monetária citada na seção {section}"

            money_val = MoneyValue(
                amount=amount,
                currency="BRL",
                is_percentage=False,
                raw_text=m.group(0),
                qualifier=qualifier,
            )

            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.VALOR,
                    normalized_value=money_val,
                    role=role,
                    confidence=0.98,
                    evidence=evidence,
                )
            )

        # 2. Extração de Percentuais (comum em sucumbência e honorários do art. 85 CPC)
        for m in REGEX_PERCENT.finditer(text):
            raw_val = m.group("val").replace(",", ".")
            try:
                pct = float(raw_val)
            except ValueError:
                continue

            ctx_start = max(0, m.start() - 80)
            context_before = text[ctx_start : m.start()].lower()

            if (
                "honor" in context_before
                or "sucumb" in context_before
                or section == "HONORARIOS_CUSTAS"
            ):
                role = EntityRole.PERCENTUAL_SUCUMBENCIA
                qualifier = "honorarios_art_85_cpc"
                evidence = "Percentual fixado para honorários advocatícios"
            else:
                role = EntityRole.VALOR_MENCIONADO
                qualifier = "percentual_generico"
                evidence = "Percentual citado no texto"

            money_val = MoneyValue(
                amount=pct,
                currency="PERCENT",
                is_percentage=True,
                raw_text=m.group(0),
                qualifier=qualifier,
            )

            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.VALOR,
                    normalized_value=money_val,
                    role=role,
                    confidence=0.95,
                    evidence=evidence,
                )
            )

        return mentions
