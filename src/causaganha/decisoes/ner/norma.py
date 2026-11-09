"""Parser Gramatical e Léxico de Referências a Normas Jurídicas Brasileiras."""

from __future__ import annotations

import re
from typing import ClassVar

from causaganha.decisoes.ner.models import EntityRole, EntityType, JudicialMention, NormaRef

# Mapeamento de diplomas e leis conhecidas
DIPLOMA_MAP = {
    "cpc": "CPC",
    "código de processo civil": "CPC",
    "codigo de processo civil": "CPC",
    "lei 13.105": "CPC",
    "cc": "CC",
    "código civil": "CC",
    "codigo civil": "CC",
    "lei 10.406": "CC",
    "cdc": "CDC",
    "código de defesa do consumidor": "CDC",
    "codigo de defesa do consumidor": "CDC",
    "lei 8.078": "CDC",
    "cf": "CF/88",
    "cf/88": "CF/88",
    "constituição federal": "CF/88",
    "constituicao federal": "CF/88",
    "constituição da república": "CF/88",
    "clt": "CLT",
    "consolidação das leis do trabalho": "CLT",
    "cp": "CP",
    "código penal": "CP",
    "codigo penal": "CP",
    "cpp": "CPP",
    "código de processo penal": "CPP",
    "lei 9.099": "LEI_9099_JUIZADOS",
    "lei 11.101": "LEI_FALENCIAS",
}

# Regex hierárquico para captura de referências a artigos
# Suporta: art. 485, § 1º, inc. VI, alínea 'a', do CPC
REGEX_ARTIGO = re.compile(
    r"\bart(?:igo|\.)?\s*(?P<art>\d+[ºoª]?)"
    r"(?:[,\s]+(?:§+|par[aá]grafo)\s*(?P<par>\d+[ºoª]?|\s*[uú]nico))?"
    r"(?:[,\s]+(?:inc(?:iso|\.)?)\s*(?P<inc>[IVXLCDM]+|\d+))?"
    r"(?:[,\s]+(?:al[ií]nea)\s*['\"]?(?P<ali>[a-zA-Z])['\"]?)?"
    r"(?:[,\s]+d[oae]\s+(?P<dip>CPC|CC|CDC|CF(?:/88)?|CLT|CP|CPP|C[oó]digo\s+(?:de\s+Processo\s+Civil|Civil|de\s+Defesa\s+do\s+Consumidor|Penal)|Lei\s+(?:n[ºo]\s*)?[\d\.]+/\d+|Lei\s+(?:n[ºo]\s*)?[\d\.]+))?",
    re.IGNORECASE,
)


class LegalReferenceParser:
    """Parser gramatical determinístico para dispositivos legais e referências normativas."""

    KNOWN_DIPLOMAS: ClassVar[list[str]] = list(DIPLOMA_MAP.keys())

    def _normalize_diploma(self, raw_dip: str | None) -> str:
        if not raw_dip:
            return "PENDENTE_CONTEXTO"
        clean = raw_dip.strip().lower()
        clean = re.sub(r"\s+", " ", clean)
        for k, v in DIPLOMA_MAP.items():
            if k in clean:
                return v
        return raw_dip.strip().upper()

    def _infer_diploma_from_surrounding_context(self, text: str, pos: int) -> str | None:
        """Busca diploma em uma janela de 250 caracteres antes ou depois para resolver referências anafóricas."""
        window_start = max(0, pos - 200)
        window_end = min(len(text), pos + 200)
        window = text[window_start:window_end].lower()

        for k, v in DIPLOMA_MAP.items():
            if re.search(r"\b" + re.escape(k) + r"\b", window):
                return v
        return None

    def extract(self, text: str, section: str = "FUNDAMENTACAO") -> list[JudicialMention]:
        mentions: list[JudicialMention] = []

        for m in REGEX_ARTIGO.finditer(text):
            art = m.group("art")
            par = m.group("par")
            inc = m.group("inc")
            ali = m.group("ali")
            raw_dip = m.group("dip")

            diploma = self._normalize_diploma(raw_dip)

            # Resolução anafórica de contexto se o diploma estiver pendente
            if diploma == "PENDENTE_CONTEXTO":
                inferred = self._infer_diploma_from_surrounding_context(text, m.start())
                if inferred:
                    diploma = inferred

            # Atribuição do Papel Semântico baseado na Seção
            if section in {"DISPOSITIVO"}:
                role = EntityRole.DISPOSITIVO_LEGAL_APLICADO
                evidence = "Citado no Dispositivo como fundamento da ordem judicial"
            elif section in {"FUNDAMENTACAO", "VOTO"}:
                role = EntityRole.RATIO_DECIDENDI
                evidence = "Citado na Fundamentação como base da ratio decidendi"
            elif section in {"RELATORIO"}:
                role = EntityRole.TESE_ALEGADA
                evidence = "Citado no Relatório nas alegações das partes"
            else:
                role = EntityRole.REFERENCIA_NORMATIVA
                evidence = f"Referência normativa na seção {section}"

            norma_val = NormaRef(
                diploma=diploma,
                artigo=art,
                paragrafo=par.strip() if par else None,
                inciso=inc.strip() if inc else None,
                alinea=ali.strip() if ali else None,
                raw_reference=m.group(0).strip(),
            )

            # Confiança: se o diploma é explícito, 0.98; se inferido por contexto, 0.90; se pendente, 0.75
            if raw_dip:
                conf = 0.98
            elif diploma != "PENDENTE_CONTEXTO":
                conf = 0.90
            else:
                conf = 0.75

            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.NORMA,
                    normalized_value=norma_val,
                    role=role,
                    confidence=conf,
                    evidence=evidence,
                )
            )

        return mentions
