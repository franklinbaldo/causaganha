"""Extrator e Vinculador de Pessoas, Advogados e OABs governados por Metadados do DJEN."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from causaganha.decisoes.ner.models import (
    EntityRole,
    EntityType,
    JudicialMention,
    OabValue,
    PersonValue,
)

VALID_UFS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}

# Regex robusta para captura de OAB em intimações reais:
# OAB nº RO5443A, OAB/RO 1234, OAB-SP 123.456, OAB/DF 12345-A, OAB 12345/RO
REGEX_OAB = re.compile(
    r"\bOAB(?:[/\s\.-]|n[ºo\.]|\s)*"
    r"(?:"
    r"(?P<uf1>[A-Za-z]{2})[^\w\n]*(?P<num1>[\d\.]{3,8})(?:[^\w\n]*(?P<tipo1>[A-Za-z]))?"
    r"|"
    r"(?P<num2>[\d\.]{3,8})[^\w\n]*(?:[/\s-]|do\s+estado\s+d[eo]\s+)?(?P<uf2>[A-Za-z]{2})(?:[^\w\n]*(?P<tipo2>[A-Za-z]))?"
    r")\b",
    re.IGNORECASE,
)

# Padrões comuns de cabeçalho para partes e advogados quando metadados forem parciais
REGEX_HEADER_ADV = re.compile(
    r"\b(?:advogada?|patron[oa]|procurador(?:a)?|advogado\s+d[oa](?:\s+\w+)?)\s*:\s*(?P<nome>[A-ZÀ-Ú][A-Za-zÀ-ú\.\s]+?)(?:,?\s*OAB|\n|$)",
    re.IGNORECASE,
)
REGEX_PRECEDING_LAWYER = re.compile(
    r"(?:advogad[oa](?:s)?(?:\s*\(a\))?(?:\s+d[oa]\s+\w+)?\s*:\s*|,\s*|\b)(?P<nome>[A-ZÀ-Ú][a-zà-úA-ZÀ-Ú\.\s]+?)(?:,\s*|\s*\(?\s*)OAB",
    re.IGNORECASE,
)
REGEX_HEADER_POLO_ATIVO = re.compile(
    r"\b(?:autor(?:a)?|requerente|exequente|embargante|impetrante|acusad[oa]|polo\s+ativo)\s*:\s*(?P<nome>[A-ZÀ-Ú][A-Za-zÀ-ú\.\s\-]+?)(?:,?\s*(?:CPF|CNPJ|endereço|residente|qualificad|[Rr][eé]u\s*:|\n|$))",
    re.IGNORECASE,
)
REGEX_HEADER_POLO_PASSIVO = re.compile(
    r"\b(?:r[eé]u|requerid[oa]|executad[oa]|embargad[oa]|impetrad[oa]|acusad[oa]|polo\s+passivo)\s*:\s*(?P<nome>[A-ZÀ-Ú][A-Za-zÀ-ú\.\s\-]+?)(?:,?\s*(?:CPF|CNPJ|endereço|residente|qualificad|\badvogad|\bOAB|\n|$))",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    clean = _strip_accents(str(name).lower())
    clean = re.sub(r"[^a-z\s]", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


class PersonAdvogadoExtractor:
    """Extrator de sujeitos processuais e patronos com ancoragem canônica nos metadados do DJEN."""

    def extract(
        self,
        text: str,
        section: str = "CABECALHO",
        metadata: dict[str, Any] | None = None,
    ) -> list[JudicialMention]:
        meta = metadata or {}
        mentions: list[JudicialMention] = []

        # 1. Recupera Partes e Advogados Oficiais do DJEN (Fonte Soberana)
        autor_djen = (
            meta.get("polo_ativo")
            or meta.get("autor")
            or meta.get("requerente")
            or meta.get("exequente")
        )
        reu_djen = (
            meta.get("polo_passivo")
            or meta.get("reu")
            or meta.get("requerido")
            or meta.get("executado")
        )
        adv_djen = meta.get("advogado") or meta.get("advogados") or meta.get("nome_advogado")
        juiz_djen = meta.get("judge_name") or meta.get("juiz") or meta.get("relator")
        oab_meta = meta.get("oab") or meta.get("numero_oab") or meta.get("numeroOAB")
        uf_oab_meta = meta.get("uf_oab") or meta.get("oab_uf") or meta.get("ufOAB")

        # Suporte ao schema estruturado de destinatários do DJEN
        destinatarios = meta.get("destinatarios") or []
        if isinstance(destinatarios, list):
            for dest in destinatarios:
                if isinstance(dest, dict):
                    nome_dest = dest.get("nome")
                    polo_code = str(dest.get("polo") or "").upper()
                    if polo_code == "A" and not autor_djen:
                        autor_djen = nome_dest
                    elif polo_code == "P" and not reu_djen:
                        reu_djen = nome_dest

        # Suporte ao schema estruturado de advogados do DJEN
        advs_list = meta.get("destinatarioadvogados") or meta.get("advogados_lista") or []
        if isinstance(advs_list, list):
            for a in advs_list:
                if isinstance(a, dict):
                    adv_obj = a.get("advogado") if isinstance(a.get("advogado"), dict) else a
                    if not adv_djen:
                        adv_djen = adv_obj.get("nome")
                    if not oab_meta:
                        oab_meta = adv_obj.get("numero_oab") or adv_obj.get("numeroOAB")
                    if not uf_oab_meta:
                        uf_oab_meta = adv_obj.get("uf_oab") or adv_obj.get("ufOAB")

        # 2. Extrai OABs presentes no texto
        for m in REGEX_OAB.finditer(text):
            uf = (m.group("uf1") or m.group("uf2") or "").upper()
            if uf not in VALID_UFS:
                continue
            raw_num = re.sub(r"\D", "", m.group("num1") or m.group("num2") or "")
            if not raw_num:
                continue
            tipo = (m.group("tipo1") or m.group("tipo2") or "").upper() or None

            # Determina o advogado: metadado oficial do DJEN ou contexto prévio no texto
            adv_name = str(adv_djen) if adv_djen else None
            if not adv_name:
                start_win = max(0, m.start() - 80)
                prefix = text[start_win : m.start() + 3]
                match_lawyer = REGEX_PRECEDING_LAWYER.search(prefix)
                if match_lawyer:
                    cand = match_lawyer.group("nome").strip()
                    cand = re.split(r":\s*", cand)[-1].strip()
                    if len(cand) > 3 and not cand.lower().startswith("oab"):
                        adv_name = cand

            oab_val = OabValue(
                uf=uf,
                numero=raw_num,
                tipo_inscricao=tipo,
                nome_advogado=adv_name,
            )

            # Verifica se bate com os metadados do DJEN
            evidence = "Inscrição na OAB identificada no texto"
            conf = 0.95
            if oab_meta and re.sub(r"\D", "", str(oab_meta)) == raw_num:
                if not uf_oab_meta or uf == str(uf_oab_meta).upper():
                    evidence = "Inscrição na OAB confirmada pelos metadados do DJEN"
                    conf = 1.0

            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.OAB,
                    normalized_value=oab_val,
                    role=EntityRole.ADVOGADO,
                    confidence=conf,
                    evidence=evidence,
                )
            )

            # Se encontrou o advogado pelo contexto prévio e ele não foi adicionado
            if adv_name and not adv_djen:
                mentions.append(
                    JudicialMention(
                        literal=adv_name,
                        start=max(0, m.start() - len(adv_name) - 10),
                        end=m.start(),
                        section=section,
                        entity_type=EntityType.PESSOA,
                        normalized_value=PersonValue(nome=adv_name, polo="ADVOGADO"),
                        role=EntityRole.ADVOGADO,
                        confidence=0.90,
                        evidence="Advogado associado à OAB identificada no texto",
                    )
                )

        # 3. Grounding das Partes Oficiais do DJEN no Texto (Correferência)
        # Se o DJEN especificou o autor, busca suas menções exatas no texto
        if autor_djen and len(str(autor_djen).strip()) > 3:
            nome_autor = str(autor_djen).strip()
            pattern = re.compile(r"\b" + re.escape(nome_autor) + r"\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                mentions.append(
                    JudicialMention(
                        literal=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        section=section,
                        entity_type=EntityType.PESSOA,
                        normalized_value=PersonValue(nome=nome_autor, polo="ATIVO"),
                        role=EntityRole.POLO_ATIVO,
                        confidence=1.0,
                        evidence=f"Polo Ativo confirmado pelos metadados oficiais do DJEN (citado em {section})",
                    )
                )

        # Se o DJEN especificou o réu, busca suas menções no texto
        if reu_djen and len(str(reu_djen).strip()) > 3:
            nome_reu = str(reu_djen).strip()
            pattern = re.compile(r"\b" + re.escape(nome_reu) + r"\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                mentions.append(
                    JudicialMention(
                        literal=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        section=section,
                        entity_type=EntityType.PESSOA,
                        normalized_value=PersonValue(nome=nome_reu, polo="PASSIVO"),
                        role=EntityRole.POLO_PASSIVO,
                        confidence=1.0,
                        evidence=f"Polo Passivo confirmado pelos metadados oficiais do DJEN (citado em {section})",
                    )
                )

        # Se o DJEN especificou advogado, busca no texto
        if adv_djen and len(str(adv_djen).strip()) > 3:
            nome_adv = str(adv_djen).strip()
            pattern = re.compile(r"\b" + re.escape(nome_adv) + r"\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                mentions.append(
                    JudicialMention(
                        literal=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        section=section,
                        entity_type=EntityType.PESSOA,
                        normalized_value=PersonValue(nome=nome_adv, polo="ADVOGADO"),
                        role=EntityRole.ADVOGADO,
                        confidence=1.0,
                        evidence="Advogado confirmado pelos metadados do DJEN",
                    )
                )

        # Se o DJEN especificou magistrado/relator, busca no texto
        if juiz_djen and len(str(juiz_djen).strip()) > 3:
            nome_juiz = str(juiz_djen).strip()
            pattern = re.compile(r"\b" + re.escape(nome_juiz) + r"\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                mentions.append(
                    JudicialMention(
                        literal=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        section=section,
                        entity_type=EntityType.PESSOA,
                        normalized_value=PersonValue(nome=nome_juiz, polo="MAGISTRADO"),
                        role=EntityRole.MAGISTRADO,
                        confidence=1.0,
                        evidence=f"Magistrado / Relator identificado pelos metadados do DJEN (seção {section})",
                    )
                )

        # 4. Fallback de Cabeçalho / Relatório: Quando metadados do DJEN não vierem com advogado ou partes,
        # detecta padrões lexicais como "Advogado: Dr. Fulano", "Autor: Beltrano", "Réu: Ciclano"
        if section in {"CABECALHO", "RELATORIO", "FUNDAMENTACAO", "CORPO"}:
            if not adv_djen:
                for m in REGEX_HEADER_ADV.finditer(text):
                    nome = m.group("nome").strip()
                    mentions.append(
                        JudicialMention(
                            literal=nome,
                            start=m.start("nome"),
                            end=m.end("nome"),
                            section=section,
                            entity_type=EntityType.PESSOA,
                            normalized_value=PersonValue(nome=nome, polo="ADVOGADO"),
                            role=EntityRole.ADVOGADO,
                            confidence=0.85,
                            evidence="Advogado extraído do rótulo de cabeçalho na ausência de metadado DJEN",
                        )
                    )

            if not autor_djen:
                for m in REGEX_HEADER_POLO_ATIVO.finditer(text):
                    nome = m.group("nome").strip()
                    if len(nome) > 3:
                        mentions.append(
                            JudicialMention(
                                literal=nome,
                                start=m.start("nome"),
                                end=m.end("nome"),
                                section=section,
                                entity_type=EntityType.PESSOA,
                                normalized_value=PersonValue(nome=nome, polo="ATIVO"),
                                role=EntityRole.POLO_ATIVO,
                                confidence=0.85,
                                evidence="Polo Ativo extraído do rótulo de cabeçalho na ausência de metadado DJEN",
                            )
                        )

            if not reu_djen:
                for m in REGEX_HEADER_POLO_PASSIVO.finditer(text):
                    nome = m.group("nome").strip()
                    if len(nome) > 3:
                        mentions.append(
                            JudicialMention(
                                literal=nome,
                                start=m.start("nome"),
                                end=m.end("nome"),
                                section=section,
                                entity_type=EntityType.PESSOA,
                                normalized_value=PersonValue(nome=nome, polo="PASSIVO"),
                                role=EntityRole.POLO_PASSIVO,
                                confidence=0.85,
                                evidence="Polo Passivo extraído do rótulo de cabeçalho na ausência de metadado DJEN",
                            )
                        )

        # 5. Detecção de Magistrado por Assinatura no Encerramento quando ausente nos metadados
        if section in {"ENCERRAMENTO", "CORPO"} and not juiz_djen:
            clean_text = text.replace("\xa0", " ")
            sig_pattern = re.compile(
                r"(?:(?:ju[ií]z(?:a)?(?:\s+de\s+direito|\s+substituto(?:a)?|\s+federal)?|desembargador(?:a)?|relator(?:a)?)\s*:\s*(?P<nome1>[A-ZÀ-Ú][a-zà-úA-ZÀ-Ú\.\s]{3,50})"
                r"|"
                r"(?:[.\n]|\b\d{4}\.?)\s*(?P<nome2>[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,4})\s+(?:Ju[ií]z(?:a)?(?:\s+de\s+Direito|\s+Substituto(?:a)?|\s+Federal)?|Desembargador(?:a)?|Relator(?:a)?)\b)",
                re.IGNORECASE,
            )
            for m in sig_pattern.finditer(clean_text):
                nome = (m.group("nome1") or m.group("nome2") or "").strip()
                if len(nome) > 4 and not any(
                    w in nome.lower() for w in ["tribunal", "comarca", "justiça", "estado"]
                ):
                    mentions.append(
                        JudicialMention(
                            literal=nome,
                            start=m.start(),
                            end=m.end(),
                            section=section,
                            entity_type=EntityType.PESSOA,
                            normalized_value=PersonValue(nome=nome, polo="MAGISTRADO"),
                            role=EntityRole.MAGISTRADO,
                            confidence=0.88,
                            evidence="Magistrado identificado por assinatura no encerramento da decisão",
                        )
                    )
                    break

        return mentions
