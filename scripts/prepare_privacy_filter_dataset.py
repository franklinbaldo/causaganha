#!/usr/bin/env python3
"""Prepare span-extraction dataset for training a judicial decision segmenter.

Reads textos.parquet from data/test_parquets, applies heuristic segmentation to
label each decision with structural spans, named entities, and legal references.

Label taxonomy (19 categories + O background = 20 labels):
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
    "O",                    # 0 — background / unlabeled
    "sec_cabecalho",        # 1 — header block (tribunal, vara, parties list)
    "sec_relatorio",        # 2 — Relatório (case history)
    "sec_fundamentacao",    # 3 — Fundamentação (legal reasoning)
    "sec_dispositivo",      # 4 — Dispositivo (operative ruling)
    "sec_assinatura",       # 5 — Signature/closing block
    "elem_nao_textual",     # 6 — non-textual elements (page numbers, repeated headers)
    "parte_autor",          # 7 — plaintiff / polo ativo name
    "parte_reu",            # 8 — defendant / polo passivo name
    "parte_terceiro",       # 9 — third party / interested party
    "nome_advogado",        # 10 — lawyer name
    "oab",                  # 11 — OAB registration number
    "nome_juiz",            # 12 — judge / magistrate name
    "cpf_cnpj",             # 13 — CPF (individual) or CNPJ (company) tax ID
    "processo_cnj",         # 14 — CNJ case number (NNNNNNN-NN.NNNN.N.NN.NNNN)
    "classe_processual",    # 15 — procedural class (Apelação Cível, etc.)
    "id_lei",               # 16 — law / statute reference (Art. X, Lei nº Y)
    "id_precedente",        # 17 — precedent identifier (Súmula X, Tema Y)
    "citacao_precedente",   # 18 — direct textual quote from a precedent
    "data",                 # 19 — date spans
]

LABEL_SPACE = {
    "category_version": "causaganha-v3",
    "span_class_names": SPAN_CLASS_NAMES,
}

# Labels that are structural sections (filled first; overwritten by entity labels)
_SECTION_LABELS: frozenset[str] = frozenset({
    "sec_cabecalho",
    "sec_relatorio",
    "sec_fundamentacao",
    "sec_dispositivo",
    "sec_assinatura",
    "elem_nao_textual",
})

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

# CPF: NNN.NNN.NNN-NN  or CNPJ: NN.NNN.NNN/NNNN-NN
_CPF_CNPJ_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")

# OAB: OAB/SP 123.456 | OAB nº 123456/SP | OAB nº RO1586 (UF antes do número)
_OAB_RE = re.compile(
    r"\bOAB\s*/\s*[A-Z]{2}\s*[\d.]+|"
    r"\bOAB\s*n[oºa°]?\s*[\d.]+/[A-Z]{2}|"
    r"\bOAB\s*n[oºa°]?\s*[A-Z]{2}\d+",
    re.IGNORECASE,
)

# Full name: title-case or ALL-CAPS words with optional prepositions (da/de/dos)
_NAME_WORD = r"[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇa-záéíóúâêîôûãõç]+"
_NAME_FULL = rf"{_NAME_WORD}(?:\s+(?:d[aeo]s?\s+)?{_NAME_WORD}){{1,5}}"
# Abbreviated initials: "J. D. D. S." style (anonymized PII in parquet)
_NAME_ABBREV = r"[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]\.(?:\s+[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ]\.){1,6}"
_NAME_ANY = rf"(?:{_NAME_FULL}|{_NAME_ABBREV})"
# Terminators: comma, semicolon, newline, paren, CPF/CNPJ, hyphen-separator, LTDA/SA
_NAME_STOP = r"(?=\s*[,;\n(]|\s+-|\s+LTDA|\s+S/A|\s+CPF|\s+CNPJ|$)"

# Polo ativo — all procedural roles that map to the active party.
# Excludes "ADVOGADOS DO …" prefixes (those go to nome_advogado).
_PARTE_AUTOR_RE = re.compile(
    r"(?:Polo\s+Ativo|Parte\s+[Aa]utor[ae]?[Ss]?|"
    r"[Aa]utor[ae]?[Ss]?|"        # Autor / Autora / Autores / Autoras
    r"[Rr]equerentes?|"            # Requerente(s)
    r"[Ee]xequentes?|"             # Exequente(s)
    r"[Aa]pelantes?|"              # Apelante(s)
    r"[Aa]gravantes?|"             # Agravante(s)
    r"[Ee]mbargantes?|"            # Embargante(s)
    r"[Ii]mpetrantes?|"            # Impetrante(s)
    r"[Rr]eclamantes?|"            # Reclamante(s)
    r"[Ii]ncidentantes?|"          # Incidentante(s)
    r"[Pp]acientes?)\s*[:-]\s*"    # Paciente(s)
    rf"({_NAME_ANY}){_NAME_STOP}",
    re.IGNORECASE,
)

# Polo passivo — all procedural roles that map to the passive party.
_PARTE_REU_RE = re.compile(
    r"(?:Polo\s+Passivo|Parte\s+[Rr][eé][aA]?[sS]?|Parte\s+[Rr]equerid[oa][sS]?|"
    r"[Rr][eé][uU][aAsS]?|"        # Réu / Ré / Réus / Reus / REU
    r"[Rr]equerid[oa][sS]?|"       # Requerido(a)(s)
    r"[Ee]xecutad[oa][sS]?|"       # Executado(a)(s)
    r"[Aa]pelad[oa][sS]?|"         # Apelado(a)(s)
    r"[Aa]gravad[oa][sS]?|"        # Agravado(a)(s)
    r"[Ee]mbargad[oa][sS]?|"       # Embargado(a)(s)
    r"[Ii]mpetrad[oa][sS]?|"       # Impetrado(a)(s)
    r"[Rr]eclamad[oa][sS]?|"       # Reclamado(a)(s)
    r"[Ii]nventariad[oa][sS]?|"    # Inventariado(a)(s)
    r"[Ii]nventariantes?)\s*[:-]\s*"  # Inventariante(s) — can be either polo
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

# Precedent citations
_PRECEDENTE_RE = re.compile(
    r"[Ss][úu]mula\s*(?:[Vv]inculante\s*)?(?:n[oºa°]?\s*)?\d+(?:\s+[A-Z]{2,4})?|"
    r"[Tt]ema\s*(?:[Rr]epetitivo\s*)?(?:n[oºa°]?\s*)?\d+(?:\s+[A-Z]{2,4})?|"
    r"[Pp]recedente\s+[Qq]ualificado\s+(?:n[oºa°]?\s*)?\d+|"
    r"[Rr]epercuss[ãa]o\s+[Gg]eral\s+(?:n[oºa°]?\s*)?\d+",
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

def _segment(text: str) -> dict[str, list[list[int]]] | None:
    """Return character-level span dict for all detectable labels.

    Entity spans overwrite section spans when they overlap — entities are
    more specific and the model benefits from seeing both layers.

    Returns None if the dispositivo section cannot be located (required anchor).
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

    # --- Pattern-based entity labels ---
    _collect(spans, "processo_cnj", _PROCESSO_CNJ_RE, text)
    _collect(spans, "cpf_cnpj", _CPF_CNPJ_RE, text)
    _collect(spans, "oab", _OAB_RE, text)
    _collect(spans, "data", _DATA_RE, text)
    _collect(spans, "id_lei", _LEI_RE, text)
    _collect(spans, "id_precedente", _PRECEDENTE_RE, text)
    _collect(spans, "classe_processual", _CLASSE_PROCESSUAL_RE, text)
    _collect(spans, "parte_autor", _PARTE_AUTOR_RE, text, group=1)
    _collect(spans, "parte_reu", _PARTE_REU_RE, text, group=1)
    _collect(spans, "nome_juiz", _JUIZ_RE, text, group=1)
    _collect(spans, "nome_advogado", _ADVOGADO_RE, text, group=1)
    _collect(spans, "nome_advogado", _ADVOGADO_HEADER_RE, text, group=1)

    return spans


def _collect(
    spans: dict[str, list[list[int]]],
    label: str,
    pattern: re.Pattern[str],
    text: str,
    group: int = 0,
) -> None:
    for m in pattern.finditer(text):
        start, end = m.start(group), m.end(group)
        if start < end:
            spans.setdefault(label, []).append([start, end])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    logger.info("starting_dataset_preparation")

    textos_file = Path("data/test_parquets/textos.parquet")
    output_dir = Path("data/privacy_filter")
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
        spans = _segment(text)
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
        logger.info("label_coverage", label=label, docs=count, pct=f"{count/len(records):.1%}")

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

    for name, data in splits.items():
        path = output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info("saved", file=str(path), count=len(data))

    label_space_path = output_dir / "label_space.json"
    label_space_path.write_text(
        json.dumps(LABEL_SPACE, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("label_space_saved", file=str(label_space_path), num_labels=len(SPAN_CLASS_NAMES))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
