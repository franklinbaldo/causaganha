#!/usr/bin/env python3
"""Extract gold-candidate segmenter records from tjro_juris parquet exports.

Real TJRO documents from the JURIS system (``src/tjro_juris``, distinct
from the DJEN-caderno-OCR source of the current 20-doc segmenter seed).
Some JURIS ``tipo`` values are structurally useful here: a ``VOTO``-tipo
document's *entire* content is a voto, an ``EMENTA``-tipo document's
entire content is an ementa, a ``RELATÓRIO``-tipo document's entire
content is a relatório — so the ``_inicio``/``_fim`` anchors sit at the
known start/end of the document, and a structural-pattern match can label
them without hunting for anchors inside a multi-page caderno.

Confirmed on a real ~18k-document sample across 2005-2023 (session
finding, not a guess): EMENTA 98.6%, RELATÓRIO 98.4%, VOTO 93.3% of
documents start with a known phrase-bank ``_inicio`` variant. The sample
also surfaced a second real closing convention this script's phrase
matching must handle: Juizados Especiais/Turmas Recursais decisions
(Lei 9.099/95) explicitly waive the formal relatório/voto closing and use
"dispensado...lei 9.099/95"/"remetam-se os autos à origem" instead of
"É o relatório."/"É o voto." — both regimes are now in
``phrase_banks.py``.

**These are heuristic-labeled CANDIDATES, not verified gold.** The
existing 20-doc train/val/test seed itself went through a
"prompt_subagents:haiku" labeling + verification pass before being
trusted (``data/segmenter_splits/manifest.json``) — candidates from this
script need the same review before merging into
``data/segmenter_splits/train.jsonl``. This script never writes there;
it only produces a separate candidates file for review.

Real party names, real process numbers, real judge names in ``info`` are
intentional, not an oversight: docs/GOVERNANCE.md already covers
preservation/reuse of public judicial text, and RFC 0011 §7's
fictionalization requirement applies to SYNTHETIC/hybrid records, not
pristine real ones.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow.parquet as pq

from scripts.synthetic_segmenter.phrase_banks import PAIR_PHRASES
from scripts.synthetic_segmenter.transform import check_final_invariants


if TYPE_CHECKING:
    from collections.abc import Iterator


# JURIS tipo -> (phrase_banks base name, doc_type). RELATÓRIO occurs in
# both sentença and acórdão (RFC 0011's guideline table) — doc_type is
# left None rather than guessed.
_TIPO_TO_BASE: dict[str, tuple[str, str | None]] = {
    "VOTO": ("voto", "acordao"),
    "EMENTA": ("ementa", "acordao"),
    "RELATÓRIO": ("relatorio", None),
}

_MIN_TEXT_LENGTH = 40

# Residual Word/OpenXML metadata clean_html() didn't fully strip (~3% of
# VOTO documents in the real sample) — reject rather than silently label
# noise as gold.
_NOISE_RE = re.compile(r"false false false|PT-BR X-NONE X-NONE|mso-", re.IGNORECASE)


def _looks_noisy(text: str) -> bool:
    """Detect residual Word/OpenXML metadata anywhere in the text.

    Confirmed via manual audit (not just the tail): the junk can sit right
    after the opening heading (e.g. "RELATÓRIO Normal 0 21 false false
    false PT-BR X-NONE X-NONE ..."), not only at the end — an
    end-only check missed it.
    """
    return bool(_NOISE_RE.search(text))


def _find_fim(text: str, fim_variants: list[str]) -> tuple[str, int, int] | None:
    """Return (surface, start, end) for the first fim variant matching the tail."""
    stripped = text.rstrip()
    for variant in fim_variants:
        if stripped.endswith(variant):
            start = len(stripped) - len(variant)
            return variant, start, start + len(variant)
    return None


def extract_candidate(row: dict, tipo: str) -> dict | None:
    """Build one gold-candidate record from a JURIS row, or None if unusable.

    Requires a matching ``_inicio`` anchor at the start; a missing
    ``_fim`` anchor still produces a record with ``unmatched_pair=True``
    (RFC 0011 §16.1 item 3 — the guideline's own "extends to EOD" case),
    not a rejection.
    """
    base, doc_type = _TIPO_TO_BASE[tipo]
    text = (row.get("texto_limpo") or "").strip()
    if len(text) < _MIN_TEXT_LENGTH or _looks_noisy(text):
        return None

    phrases = PAIR_PHRASES[base]
    inicio_match = next((p for p in phrases["inicio"] if text.startswith(p)), None)
    if inicio_match is None:
        return None

    labels = [
        {"category": f"{base}_inicio", "start": 0, "end": len(inicio_match)},
    ]
    unmatched_pair = True
    fim = _find_fim(text, phrases["fim"])
    if fim is not None:
        _surface, fim_start, fim_end = fim
        labels.append({"category": f"{base}_fim", "start": fim_start, "end": fim_end})
        unmatched_pair = False

    problems = check_final_invariants(text, labels)
    if problems:
        return None

    info = {
        "source": "tjro_juris",
        "tipo": tipo,
        "id_documento": row.get("id_documento"),
        "nr_processo": row.get("nr_processo"),
        "classe_judicial": row.get("classe_judicial"),
        "orgao": row.get("orgao"),
        "relator": row.get("relator"),
        "unmatched_pair": unmatched_pair,
    }
    if doc_type is not None:
        info["doc_type"] = doc_type

    return {"text": text, "label": labels, "info": info}


def _find_internal(text: str, variants: list[str]) -> tuple[str, int, int] | None:
    """Return (surface, start, end) for the earliest-occurring variant anywhere in text."""
    best: tuple[str, int, int] | None = None
    for variant in variants:
        idx = text.find(variant)
        if idx != -1 and (best is None or idx < best[1]):
            best = (variant, idx, idx + len(variant))
    return best


def extract_internal_candidate(row: dict, base: str) -> dict | None:
    """Build a candidate by searching ANYWHERE in a composite ACÓRDÃO-tipo document.

    Unlike ``extract_candidate`` (whole-document-is-the-category), this is
    for categories embedded partway through a longer real document — e.g.
    ``acordao_decisorio``'s "Vistos, relatados e discutidos ... À
    UNANIMIDADE." dispositivo line inside a full ACÓRDÃO text. Only safe
    for categories whose phrase-bank variants are unambiguous substrings
    everywhere they occur; ``preliminar`` is deliberately NOT wired
    through this path — "PRELIMINAR" alone also appears as a dispositivo
    outcome word ("PRELIMINAR REJEITADA"), which is not the section
    heading this category means, and disambiguating that needs a
    different, narrower pattern than a shared-phrase-bank substring match.
    """
    text = (row.get("texto_limpo") or "").strip()
    if len(text) < _MIN_TEXT_LENGTH or _looks_noisy(text):
        return None

    phrases = PAIR_PHRASES[base]
    inicio = _find_internal(text, phrases["inicio"])
    if inicio is None:
        return None
    _inicio_surface, inicio_start, inicio_end = inicio

    labels = [{"category": f"{base}_inicio", "start": inicio_start, "end": inicio_end}]
    unmatched_pair = True
    fim = _find_internal(text[inicio_end:], phrases["fim"])
    if fim is not None:
        _fim_surface, rel_start, rel_end = fim
        labels.append(
            {
                "category": f"{base}_fim",
                "start": inicio_end + rel_start,
                "end": inicio_end + rel_end,
            }
        )
        unmatched_pair = False

    problems = check_final_invariants(text, labels)
    if problems:
        return None

    info = {
        "source": "tjro_juris",
        "tipo": "ACÓRDÃO",
        "id_documento": row.get("id_documento"),
        "nr_processo": row.get("nr_processo"),
        "classe_judicial": row.get("classe_judicial"),
        "orgao": row.get("orgao"),
        "relator": row.get("relator"),
        "unmatched_pair": unmatched_pair,
        "doc_type": "acordao",
        "extraction_mode": "internal",
    }
    return {"text": text, "label": labels, "info": info}


def extract_from_parquet(path: Path, tipo: str) -> Iterator[dict]:
    """Yield gold candidates from every usable row in a JURIS parquet file."""
    table = pq.read_table(str(path))
    for row in table.to_pylist():
        candidate = extract_candidate(row, tipo)
        if candidate is not None:
            yield candidate


def extract_internal_from_parquet(path: Path, base: str) -> Iterator[dict]:
    """Yield internal-search candidates for ``base`` from an ACÓRDÃO-tipo parquet file."""
    table = pq.read_table(str(path))
    for row in table.to_pylist():
        candidate = extract_internal_candidate(row, base)
        if candidate is not None:
            yield candidate


def _tipo_from_filename(path: Path) -> str:
    for tipo in _TIPO_TO_BASE:
        if tipo in path.stem:
            return tipo
    msg = f"could not infer JURIS tipo from filename {path.name!r}"
    raise ValueError(msg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet", nargs="+", help="tjro_juris parquet file(s) to extract from.")
    parser.add_argument("--out", required=True, help="Output candidates JSONL path.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    matched_both = 0
    matched_inicio_only = 0
    with out_path.open("w", encoding="utf-8") as f:
        for parquet_path in args.parquet:
            path = Path(parquet_path)
            tipo = _tipo_from_filename(path)
            table = pq.read_table(str(path))
            total_rows += table.num_rows
            for candidate in extract_from_parquet(path, tipo):
                if candidate["info"]["unmatched_pair"]:
                    matched_inicio_only += 1
                else:
                    matched_both += 1
                f.write(json.dumps(candidate, ensure_ascii=False))
                f.write("\n")

    total_candidates = matched_both + matched_inicio_only
    print(f"rows scanned: {total_rows}")
    print(
        f"candidates written: {total_candidates} "
        f"(inicio+fim: {matched_both}, inicio-only: {matched_inicio_only})"
    )
    print(f"rejected (no inicio match / noise / too short): {total_rows - total_candidates}")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
