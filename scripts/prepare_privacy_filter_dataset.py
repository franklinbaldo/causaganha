#!/usr/bin/env python3
"""Prepare span-extraction dataset for training a judicial decision segmenter.

Reads textos.parquet from data/test_parquets, applies heuristic segmentation to
label each decision with structural spans, named entities, and legal references.

Label taxonomy (21 categories + O background = 22 labels):
  Sections   : sec_cabecalho, sec_relatorio, sec_fundamentacao,
                sec_dispositivo, sec_assinatura
  Non-text   : elem_nao_textual
  Parties    : parte_autor, parte_reu, parte_terceiro
  Personnel  : nome_advogado, oab, nome_juiz
  PII        : cpf_cnpj
  Legal meta : processo_cnj, classe_processual, id_lei,
                id_precedente, citacao_precedente
  Temporal   : data

Heuristic coverage per label:
  ✓ All structural sections (regex boundary markers)
  ✓ processo_cnj, cpf_cnpj, oab, data, id_lei, id_precedente,
    classe_processual  (pattern-based)
  ~ nome_advogado  (adjacent-to-OAB heuristic, partial)
  ✗ parte_autor, parte_reu, parte_terceiro, nome_juiz,
    citacao_precedente, elem_nao_textual  (need LLM or NER pass)

Output format is compatible with both:
  - opf train  (openai/privacy-filter CLI, --label-space-json)
  - HuggingFace Trainer  (token classification with 20 classes)

Usage:
    uv run python scripts/prepare_privacy_filter_dataset.py
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

import ibis
import structlog


logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Label space definition
# ---------------------------------------------------------------------------

SPAN_CLASS_NAMES: list[str] = [
    "O",  # 0 — background / unlabeled
    "sec_cabecalho",  # 1 — header block (tribunal, vara, parties list)
    "sec_relatorio",  # 2 — Relatório (case history)
    "sec_fundamentacao",  # 3 — Fundamentação (legal reasoning)
    "sec_dispositivo",  # 4 — Dispositivo (operative ruling)
    "sec_assinatura",  # 5 — Signature/closing block
    "elem_nao_textual",  # 6 — non-textual elements (page numbers, repeated headers)
    "parte_autor",  # 7 — plaintiff / polo ativo name
    "parte_reu",  # 8 — defendant / polo passivo name
    "parte_terceiro",  # 9 — third party / interested party
    "nome_advogado",  # 10 — lawyer name
    "oab",  # 11 — OAB registration number
    "nome_juiz",  # 12 — judge / magistrate name
    "cpf_cnpj",  # 13 — CPF (individual) or CNPJ (company) tax ID
    "processo_cnj",  # 14 — CNJ case number (NNNNNNN-NN.NNNN.N.NN.NNNN)
    "classe_processual",  # 15 — procedural class (Apelação Cível, etc.)
    "id_lei",  # 16 — law / statute reference (Art. X, Lei nº Y)
    "id_precedente",  # 17 — precedent identifier (Súmula X, Tema Y)
    "citacao_precedente",  # 18 — direct textual quote from a precedent
    "data",  # 19 — date spans
    "serventuario",  # 20 — court clerk / officer who signs instead of judge
    "valor_monetario",  # 21 — monetary value in Brazilian Reais (R$)
]

LABEL_SPACE = {
    "category_version": "causaganha-v4",
    "span_class_names": SPAN_CLASS_NAMES,
}

# Labels that are structural sections (filled first; overwritten by entity labels)
_SECTION_LABELS: frozenset[str] = frozenset(
    {
        "sec_cabecalho",
        "sec_relatorio",
        "sec_fundamentacao",
        "sec_dispositivo",
        "sec_assinatura",
        "elem_nao_textual",
    }
)

# ---------------------------------------------------------------------------
# Structural section markers
# ---------------------------------------------------------------------------

_DISPOSITIVO_RE = re.compile(
    r"(?:ante\s+(?:todo\s+o|ao|o)\s+exposto|posto\s+isso|isso\s+posto|"
    r"isto\s+posto|diante\s+do\s+exposto|pelo\s+exposto|"
    r"em\s+face\s+do\s+exposto|por\s+tais\s+fundamentos|"
    r"nestes\s+termos|em\s+conclus[ãa]o|pelo\s+que\s+exposto|"
    r"em\s+vista\s+do\s+exposto|por\s+(?:todo\s+o\s+)?exposto|"
    r"por\s+essas\s+raz[oõ]es|em\s+raz[aã]o\s+do\s+exposto|"
    r"\bDECIDO\b)",
    re.IGNORECASE,
)

_FUNDAMENTACAO_RE = re.compile(
    r"(?:fundament[ao](?:ção)?|m[eé]rito|an[aá]lise\s+do\s+pedido|"
    r"da\s+an[aá]lise|do\s+m[eé]rito|"
    r"fundamenta[çc][aã]o\s+(?:jur[ií]dica|do\s+ju[ií]zo))",
    re.IGNORECASE,
)

_RELATORIO_MARKER_RE = re.compile(
    r"(?:\brelat[oó]rio\b|trata-se\s+de|cuida-se\s+de|vistos?\s+etc|"
    r"em\s+an[aá]lise\s+o\s+feito|em\s+julgamento\s+o\s+feito|"
    r"\bRELAT[ÓO]RIO\b)",
    re.IGNORECASE,
)

# City + date pattern signals the start of the signature block
_ASSINATURA_RE = re.compile(
    r"(?:[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][a-záéíóúâêîôûãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][a-záéíóúâêîôûãõç]+)?"
    r"\s*,\s*\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|"
    r"julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Named entity / legal reference patterns
# ---------------------------------------------------------------------------

# CNJ case number: NNNNNNN-NN.NNNN.N.NN.NNNN
_PROCESSO_CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")

# CPF: NNN.NNN.NNN-NN or bare 11 digits after "CPF nº"
# CNPJ: NN.NNN.NNN/NNNN-NN or bare 14 digits after "CNPJ nº"
_CPF_CNPJ_RE = re.compile(
    r"\d{3}\.\d{3}\.\d{3}-\d{2}"
    r"|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"
    r"|(?:CPF|CNPJ)\s*n[oº°]?\s*[\d./-]{9,19}",
    re.IGNORECASE,
)

# OAB: OAB/SP 123.456 | OAB nº 123456/SP | OAB nº RO1586 (UF antes do número)
_OAB_RE = re.compile(
    r"\bOAB\s*/\s*[A-Z]{2}\s*[\d.]+|"
    r"\bOAB\s*n[oºa°]?\s*[\d.]+/[A-Z]{2}|"
    r"\bOAB\s*n[oºa°]?\s*[A-Z]{2}\d+",
    re.IGNORECASE,
)

# Full name: title-case or ALL-CAPS words with optional prepositions (da/de/dos)
_NAME_WORD = r"[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇa-záéíóúâêîôûãõç]+"
_NAME_FULL = rf"{_NAME_WORD}(?:\s+(?:(?:d[aeo]s?|e)\s+)?{_NAME_WORD}){{1,5}}"
# Abbreviated initials: "J. D. D. S." style (anonymized PII in parquet)
_NAME_ABBREV = r"[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]\.(?:\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]\.){1,6}"
_NAME_ANY = rf"(?:{_NAME_FULL}|{_NAME_ABBREV})"
# Terminators: comma, semicolon, colon, newline, paren, CPF/CNPJ, hyphen, LTDA/SA,
# or field-label keywords (ADVOGADO, PROCURADORIA) that follow names in cabecalho.
_NAME_STOP = r"(?=\s*[,;:\n(]|\s+-|\s+LTDA|\s+S/A|\s+CPF|\s+CNPJ|\s+ADVOGADO|\s+PROCURADORIA|$)"

# Polo ativo — all procedural roles that map to the active party.
# Excludes "ADVOGADOS DO …" prefixes (those go to nome_advogado).
_PARTE_AUTOR_RE = re.compile(
    r"(?:Polo\s+Ativo|Parte\s+[Aa]utor[ae]?[Ss]?|"
    r"[Aa]utor[ae]?[Ss]?|"  # Autor / Autora / Autores / Autoras
    r"[Rr]equerentes?|"  # Requerente(s)
    r"[Ee]xequentes?|"  # Exequente(s)
    r"[Aa]pelantes?|"  # Apelante(s)
    r"[Aa]gravantes?|"  # Agravante(s)
    r"[Ee]mbargantes?|"  # Embargante(s)
    r"[Ii]mpetrantes?|"  # Impetrante(s)
    r"[Rr]eclamantes?|"  # Reclamante(s)
    r"[Ii]ncidentantes?|"  # Incidentante(s)
    r"[Pp]acientes?)(?:\s*\([aosSAS]+\))?\s*[:-]\s*"  # Paciente(s) + optional (a)/(s) suffix
    rf"({_NAME_ANY}){_NAME_STOP}",
    re.IGNORECASE,
)

# Polo passivo — all procedural roles that map to the passive party.
_PARTE_REU_RE = re.compile(
    r"(?:Polo\s+Passivo|Parte\s+[Rr][eé][aA]?[sS]?|Parte\s+[Rr]equerid[oa][sS]?|"
    r"[Rr][eé][uU][aAsS]?|"  # Réu / Ré / Réus / Reus / REU
    r"[Rr]equerid[oa][sS]?|"  # Requerido(a)(s)
    r"[Ee]xecutad[oa][sS]?|"  # Executado(a)(s)
    r"[Aa]pelad[oa][sS]?|"  # Apelado(a)(s)
    r"[Aa]gravad[oa][sS]?|"  # Agravado(a)(s)
    r"[Ee]mbargad[oa][sS]?|"  # Embargado(a)(s)
    r"[Ii]mpetrad[oa][sS]?|"  # Impetrado(a)(s)
    r"[Rr]eclamad[oa][sS]?|"  # Reclamado(a)(s)
    r"[Ii]nventariad[oa][sS]?|"  # Inventariado(a)(s)
    r"[Ii]nventariantes?)(?:\s*\([aosSAS]+\))?\s*[:-]\s*"  # optional (a)/(s) suffix
    rf"({_NAME_ANY}){_NAME_STOP}",
    re.IGNORECASE,
)

# Juiz assina no final: nome ANTES do título, separados por espaço ou newline.
# Ex: "Ana Lucia Mortari Juíza Substituta" ou "Hugo Hollanda Soares\nJuiz de Direito"
_JUIZ_RE = re.compile(
    r"(?:[Dd]r[oa]?\.?\s+)?"
    rf"({_NAME_FULL})[\s\n]+"
    r"(?:[Jj]u[ií][zs][ae]?(?:\([aA]\))?(?:\s+de\s+[Dd]ireito)?(?:\s+[Ss]ubstitut[oa])?|"
    r"[Mm]agistrad[oa](?:\s+[Ss]ubstitut[oa])?|"
    r"[Dd]esembargador[ae]?(?:\s+[Rr]elator[ae]?)?|"
    r"[Dd]es\.\s*[Rr]elator[ae]?)\b",
    re.IGNORECASE,
)

# Serventuário: assina no lugar do juiz — mesmo padrão (nome antes do título)
# Títulos: Escrivão/ã, Oficial de Justiça, Diretor/a de Secretaria/Cartório,
#          Analista/Técnico/Assistente Judiciário, Secretário/a de Vara
_SERVENTUARIO_RE = re.compile(
    r"(?:[Dd]r[oa]?\.?\s+)?"
    rf"({_NAME_FULL})[\s\n]+"
    r"(?:[Ee]scriv[ãa][oe]?|"
    r"[Oo]ficial\s+de\s+[Jj]usti[çc]a|"
    r"[Dd]iretor[ae]?\s+de\s+(?:[Ss]ecretaria|[Cc]art[oó]rio)|"
    r"[Cc]hefe\s+de\s+[Ss]ecretaria|"
    r"[Ss]ecret[aá]ri[oa]\s+de\s+[Vv]ara|"
    r"[Ss]ecret[aá]ri[oa]\s+[Jj]udici[aá]ri[oa]|"
    r"[Aa]nalista\s+[Jj]udici[aá]ri[oa]|"
    r"[Tt][eé]cnico\s+[Jj]udici[aá]ri[oa]|"
    r"[Aa]ssistente\s+[Jj]udici[aá]ri[oa]|"
    r"[Ss]erventu[aá]ri[oa])\b",
    re.IGNORECASE,
)

# Valor monetário em reais: R$ 1.234,56  ou  R$1.234,56  ou  R$ 1.234.567,89
_VALOR_RE = re.compile(
    r"R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}"
    r"|R\$\s*\d+,\d{2}",
)

# Advogados: (1) nome antes de OAB | (2) "ADVOGADOS DO AUTOR/RÉU: NOME"
_ADVOGADO_RE = re.compile(
    r"(?:[Dd]r[oa]?\.?\s+|[Aa]dv\.?\s+)?"
    rf"({_NAME_FULL})"
    r"(?=\s*,?\s*OAB)",
)
_ADVOGADO_HEADER_RE = re.compile(
    r"ADVOGAD[OSas]+\s+D[AOaoe][Ss]?\s+"
    r"(?:AUTOR[AES]*|REU|R[EÉeé]U[AS]?|EXEQUENTES?|REQUERENTES?|"
    r"REQUERID[OA]S?|EXECUTAD[OA]S?|APELAD[OA]S?|AGRAVAD[OA]S?|"
    r"EMBARGAD[OA]S?|IMPETRAD[OA]S?|RECLAMAD[OA]S?)\s*[:-]\s*"
    rf"({_NAME_FULL}){_NAME_STOP}",
    re.IGNORECASE,
)

# Dates: long form (15 de janeiro de 2024) or short form (15/01/2024)
_DATA_RE = re.compile(
    r"\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|abril|maio|junho|"
    r"julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4}|"
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE,
)

# Law / statute references
_LEI_RE = re.compile(
    r"[Aa]rt(?:igo)?\.?\s*\d+(?:[,\s]*[§ºa°]\s*\d+)*"
    r"(?:\s+(?:do|da|de)\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][a-záéíóúâêîôûãõç]+(?:\s+[a-záéíóúâêîôûãõç]+){0,3})?|"
    r"[Ll]ei\s+(?:[Cc]omplementar\s+)?(?:n[oºa°]?\s*)?[\d.]+/\d{2,4}|"
    r"[Dd]ecreto(?:-[Ll]ei)?\s+(?:n[oºa°]?\s*)?[\d.]+(?:/\d{2,4})?|"
    r"\b(?:CPC|CC|CDC|CLT|CF|CTN|CP|CPP|ECA|LRF|LINDB)\b",
)

# Precedent citations: Súmula, Tema, REsp, HC, RE, etc.
_PRECEDENTE_RE = re.compile(
    r"[Ss][úu]mula\s*(?:[Vv]inculante\s*)?(?:n[oºa°]?\s*)?\d+(?:\s+[A-Z]{2,4})?|"
    r"[Tt]ema\s*(?:[Rr]epetitivo\s*)?(?:n[oºa°]?\s*)?\d+(?:\s+[A-Z]{2,4})?|"
    r"[Pp]recedente\s+[Qq]ualificado\s+(?:n[oºa°]?\s*)?\d+|"
    r"[Rr]epercuss[ãa]o\s+[Gg]eral\s+(?:n[oºa°]?\s*)?\d+|"
    # STJ/STF case identifiers: REsp 1234/SP, AREsp 1.234.456-MG, HC 123456 etc.
    r"(?:REsp|AREsp|AgRg|AgInt|EREsp|HC|RO|MS|RE|ADI|ADPF|RTJ|RESP)"
    r"\s*[-nº°]?\s*[\d.,]+(?:[/-][A-Z]{2})?",
    re.IGNORECASE,
)

# Procedural class names
_CLASSE_PROCESSUAL_RE = re.compile(
    r"[Aa]pela[çc][ãa]o\s+[Cc][íi]vel|"
    r"[Aa]pela[çc][ãa]o\s+[Cc]riminal|"
    r"[Aa][çc][ãa]o\s+[Oo]rdin[áa]ria|"
    r"[Pp]rocedimento\s+[Cc]omum\s+[Cc][íi]vel|"
    r"[Aa]gravo\s+de\s+[Ii]nstrumento|"
    r"[Aa]gravo\s+[Rr]egimental|"
    r"[Aa]gravo\s+[Ii]nterno|"
    r"[Ee]mbargos\s+de\s+[Dd]eclara[çc][ãa]o|"
    r"[Ee]mbargos\s+[Àa]\s+[Ee]xecu[çc][ãa]o|"
    r"[Jj]uizado\s+[Ee]special(?:\s+[Cc][íi]vel)?|"
    r"[Cc]umprimento\s+de\s+[Ss]enten[çc]a|"
    r"[Ee]xecu[çc][ãa]o\s+[Ff]iscal|"
    r"[Ee]xecu[çc][ãa]o\s+de\s+[Tt][íi]tulo\s+[Ee]xtrajudicial|"
    r"[Hh]abeas\s+[Cc]orpus|"
    r"[Hh]abeas\s+[Dd]ata|"
    r"[Mm]andado\s+de\s+[Ss]eguran[çc]a|"
    r"[Mm]andado\s+de\s+[Ii]njun[çc][ãa]o|"
    r"[Aa][çc][ãa]o\s+[Pp]opular|"
    r"[Aa][çc][ãa]o\s+[Cc]ivil\s+[Pp][úu]blica|"
    r"[Rr]ecurso\s+[Ee]special|"
    r"[Rr]ecurso\s+[Ee]xtraordin[áa]rio|"
    r"[Rr]ecurso\s+[Oo]rdin[áa]rio",
)


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------


def _segment(text: str, fp_filter: object = None) -> dict[str, list[list[int]]] | None:
    """Return character-level span dict for all detectable labels.

    Entity spans overwrite section spans when they overlap — entities are
    more specific and the model benefits from seeing both layers.

    Returns None if the dispositivo section cannot be located (required anchor).
    ``fp_filter`` is an optional :class:`FPCentroidFilter` for embedding-based
    FP rejection on ambiguous labels.
    """
    spans: dict[str, list[list[int]]] = {}

    # --- Structural sections ---
    dispositivo_match = _DISPOSITIVO_RE.search(text)
    if not dispositivo_match:
        return None

    dispositivo_start = dispositivo_match.start()
    pre_disp = text[:dispositivo_start]

    fund_match = _FUNDAMENTACAO_RE.search(pre_disp)
    fund_start = fund_match.start() if fund_match else len(pre_disp) // 2

    rel_match = _RELATORIO_MARKER_RE.search(text[:fund_start])
    cabecalho_end = rel_match.start() if rel_match else min(400, fund_start // 3)
    relatorio_start = cabecalho_end

    assin_match = _ASSINATURA_RE.search(text, dispositivo_start)
    assin_start = assin_match.start() if assin_match else len(text)

    if cabecalho_end > 0:
        spans["sec_cabecalho"] = [[0, cabecalho_end]]
    if fund_start > relatorio_start:
        spans["sec_relatorio"] = [[relatorio_start, fund_start]]
    if dispositivo_start > fund_start:
        spans["sec_fundamentacao"] = [[fund_start, dispositivo_start]]
    if assin_start > dispositivo_start:
        spans["sec_dispositivo"] = [[dispositivo_start, assin_start]]
    if assin_start < len(text):
        spans["sec_assinatura"] = [[assin_start, len(text)]]

    # --- Pattern-based entity labels (section-gated where possible) ---
    # Unrestricted: these labels can appear anywhere in the document
    _collect(spans, "processo_cnj", _PROCESSO_CNJ_RE, text)
    _collect(spans, "data", _DATA_RE, text)
    _collect(spans, "valor_monetario", _VALOR_RE, text)
    _collect(spans, "cpf_cnpj", _CPF_CNPJ_RE, text)

    # Legal references: skip cabecalho (party lists, addresses) and assinatura
    body_start = cabecalho_end
    _collect(spans, "id_lei", _LEI_RE, text, start=body_start, end=assin_start)
    _collect(
        spans,
        "id_precedente",
        _PRECEDENTE_RE,
        text,
        start=body_start,
        end=assin_start,
        fp_filter=fp_filter,
        fp_label="id_precedente",
    )
    _collect(spans, "classe_processual", _CLASSE_PROCESSUAL_RE, text, end=fund_start)
    _collect(spans, "oab", _OAB_RE, text, end=assin_start)

    # Parties: cabecalho + early relatorio only.
    # Rule-based filter: skip spans where "ADVOGADO" precedes the keyword —
    # those are lawyer names mislabeled as parties (embedding centroid cannot
    # distinguish this case reliably due to structural similarity).
    _collect_parties(spans, text, end=fund_start)

    # Lawyer names: before assinatura
    _collect(spans, "nome_advogado", _ADVOGADO_RE, text, group=1, end=assin_start)
    _collect(spans, "nome_advogado", _ADVOGADO_HEADER_RE, text, group=1, end=assin_start)

    # Judge / clerk: only after dispositivo (signature block)
    _collect(spans, "nome_juiz", _JUIZ_RE, text, group=1, start=dispositivo_start)
    _collect(spans, "serventuario", _SERVENTUARIO_RE, text, group=1, start=dispositivo_start)

    return spans


try:
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).parent))
    from fp_centroid_filter import FPCentroidFilter as _FPCentroidFilter
except ImportError:
    _FPCentroidFilter = None  # type: ignore[assignment,misc]


def _collect(
    spans: dict[str, list[list[int]]],
    label: str,
    pattern: re.Pattern[str],
    text: str,
    group: int = 0,
    *,
    start: int = 0,
    end: int | None = None,
    fp_filter: object = None,
    fp_label: str | None = None,
) -> None:
    """Find pattern matches and append [start, end] spans.

    ``start`` / ``end`` gate the search to a document sub-region.
    ``fp_filter`` + ``fp_label`` enable embedding-based FP rejection:
    spans whose context is too similar to the label's FP centroid are dropped.
    """
    if end is None:
        end = len(text)
    candidates: list[tuple[int, int]] = []
    for m in pattern.finditer(text, start, end):
        s, e = m.start(group), m.end(group)
        if s < e:
            candidates.append((s, e))

    if not candidates:
        return

    if fp_filter is not None and fp_label:
        keep = fp_filter.bulk_is_fp(fp_label, text, candidates)  # type: ignore[union-attr]
        for (s, e), is_fp in zip(candidates, keep, strict=True):
            if not is_fp:
                spans.setdefault(label, []).append([s, e])
    else:
        for s, e in candidates:
            spans.setdefault(label, []).append([s, e])


# "ADVOGADO DO" or "ADVOGADOS DO" immediately before the matched role keyword.
# Uses end-anchor ($) so it only fires when ADVOGADO DO is the last thing
# before the keyword — avoids false rejection when a previous line had
# "ADVOGADO DO AUTOR: nome\n" and the current line is "AUTOR: party".
_ADVOGADO_IMMEDIATE = re.compile(r"ADVOGAD[OS]+\s+D[OA]\s+$", re.IGNORECASE)
_ADVOGADO_LOOKBACK = 30  # chars before keyword start to examine


def _collect_parties(
    spans: dict[str, list[list[int]]],
    text: str,
    end: int,
) -> None:
    """Collect parte_autor and parte_reu with ADVOGADO-context filter.

    Rejects spans where "ADVOGADO DO/S" ends immediately before the role
    keyword: e.g. "ADVOGADO DO REQUERIDO: nome" → the name is the lawyer.
    Does NOT reject when ADVOGADO appeared on a prior line.
    """
    for label, regex in (
        ("parte_autor", _PARTE_AUTOR_RE),
        ("parte_reu", _PARTE_REU_RE),
    ):
        for m in regex.finditer(text, 0, end):
            preceding = text[max(0, m.start() - _ADVOGADO_LOOKBACK) : m.start()]
            if _ADVOGADO_IMMEDIATE.search(preceding):
                continue
            s, e = m.start(1), m.end(1)
            if s < e:
                spans.setdefault(label, []).append([s, e])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    logger.info("starting_dataset_preparation")

    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", default="data/test_parquets/textos.parquet")
    parser.add_argument("--output", default="data/privacy_filter/train.jsonl")
    parser.add_argument("--label-space", default="data/privacy_filter/label_space.json")
    parser.add_argument(
        "--fp-filter",
        metavar="PATH",
        nargs="?",
        const="auto",
        help="Enable embedding-based FP filter. Pass a .pkl path to load "
        "precomputed centroids, or omit path to fit from the built-in catalog.",
    )
    args = parser.parse_args()

    # Wire up the FP filter if requested
    fp_filter = None
    if args.fp_filter and _FPCentroidFilter is not None:
        fp_filter = _FPCentroidFilter()
        centroids_pkl = Path("data/privacy_filter/fp_centroids.pkl")
        if args.fp_filter != "auto" and Path(args.fp_filter).exists():
            logger.info("fp_filter_loading", path=args.fp_filter)
            fp_filter.load(args.fp_filter)
        elif centroids_pkl.exists():
            logger.info("fp_filter_loading", path=str(centroids_pkl))
            fp_filter.load(centroids_pkl)
        else:
            logger.info("fp_filter_fitting_from_catalog")
            fp_filter.fit_from_catalog()
            fp_filter.save(centroids_pkl)
            logger.info("fp_filter_saved", path=str(centroids_pkl))
    elif args.fp_filter:
        logger.warning("fp_filter_unavailable", reason="fp_centroid_filter module not found")

    textos_file = Path(args.parquet)
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    if not textos_file.exists():
        logger.error("textos_parquet_missing", path=str(textos_file))
        return 1

    logger.info("loading_textos_parquet")
    t = ibis.read_parquet(textos_file)
    df = t.filter(t.texto.notnull()).execute()
    logger.info("textos_loaded", count=len(df))

    records: list[dict] = []
    skipped = 0

    for _, row in df.iterrows():
        text: str = row["texto"]
        spans = _segment(text, fp_filter=fp_filter)
        if spans is None:
            skipped += 1
            continue
        records.append({"text": text, "spans": spans})

    logger.info("segmentation_complete", total=len(records), skipped=skipped)

    if not records:
        logger.error("no_records_to_write")
        return 1

    # Log coverage per label
    label_coverage: dict[str, int] = {}
    for rec in records:
        for label in rec["spans"]:
            label_coverage[label] = label_coverage.get(label, 0) + 1
    for label, count in sorted(label_coverage.items()):
        logger.info("label_coverage", label=label, docs=count, pct=f"{count / len(records):.1%}")

    random.seed(42)
    random.shuffle(records)

    n = len(records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    splits = {
        "train": records[:train_end],
        "validation": records[train_end:val_end],
        "test": records[val_end:],
    }
    logger.info("splitting", **{k: len(v) for k, v in splits.items()})

    stem = Path(args.output).stem  # e.g. "train"
    for name, data in splits.items():
        fname = stem if name == "train" else name
        path = output_dir / f"{fname}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info("saved", file=str(path), count=len(data))

    label_space_path = Path(args.label_space)
    label_space_path.parent.mkdir(parents=True, exist_ok=True)
    label_space_path.write_text(
        json.dumps(LABEL_SPACE, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("label_space_saved", file=str(label_space_path), num_labels=len(SPAN_CLASS_NAMES))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
