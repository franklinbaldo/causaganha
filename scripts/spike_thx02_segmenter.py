"""Experimental THX-02 region segmenter for Brazilian judicial documents.

The THX-02 API is a *classifier*, not a span/offset extractor. This prototype
splits text deterministically with exact source offsets, asks THX-02 for a role
for each unit, and merges consecutive units of the same role into regions.

Offline by default: no HTTP or data transmission unless --live is supplied.
Never part of the production pipeline or published as an OPF benchmark.

    python scripts/spike_thx02_segmenter.py
    python scripts/spike_thx02_segmenter.py --audit-train data/segmenter_splits/train.jsonl
    python scripts/spike_thx02_segmenter.py --live --source tests/fixtures/thx02_segmenter_synthetic.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

ENDPOINT = "https://api.hal-x.ai/v1/decide/batch"
MAX_UNITS_PER_REQUEST = 60  # Anonymous quota is 60 *questions* per minute/IP.
ROLES: dict[str, str] = {
    "cabecalho": "Identity, court, parties, case number or formal document header.",
    "ementa": "Case law syllabus/ementa summarizing the judgment and holdings.",
    "relatorio": "Neutral report of the case, facts, requests and procedural history.",
    "fundamentacao": "Judicial legal analysis, grounds and reasons for deciding the case.",
    "preliminar": "Preliminary procedural issue, admissibility or jurisdictional objection.",
    "voto": "Individual judge's vote in a collegiate appellate decision.",
    "dispositivo": "Present operative ruling, order or disposition by the deciding court.",
    "custas": "Current decision's ruling about court fees and costs.",
    "honorarios": "Current decision's ruling about attorneys' fees.",
    "encerramento": "Signature, city/date, publication or procedural closing formulas.",
    "outro": "Unclassifiable text, boilerplate or a mix that fits no one role.",
}

# A generous, deliberately explicit break: headings and paragraph starts, then
# sentence boundaries in overlong text. No stripping/normalization changes offsets.
_HEADING = re.compile(
    r"(?i)(?:^|(?<=\s))(?:(?:[IVX]{1,5})\s*[-–—.]\s*)?"
    r"(?:RELAT[ÓO]RIO|FUNDAMENTA[CÇ][ÃA]O|DISPOSITIVO|EMENTA|VOTO|AC[ÓO]RD[ÃA]O)\b"
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?;])\s+(?=[A-ZÀ-Ü0-9])")
_ABBREVIATIONS = re.compile(r"(?i)(?:\bart|\barts|\bdr|\bdra|\bn|\bnum|\bfls|\bdes|\brel)\.$")


@dataclass(frozen=True, slots=True)
class Unit:
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class Prediction:
    start: int
    end: int
    label: str
    probability: float
    status: str  # accepted | abstained | unavailable


def _clean_unit(text: str, start: int, end: int) -> Unit | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start == end:
        return None
    return Unit(start, end, text[start:end])


def split_units(text: str, *, max_chars: int = 600) -> list[Unit]:
    """Return non-overlapping source-aligned units (not gold segmentation)."""
    if max_chars < 80:
        raise ValueError("max_chars must be >= 80")
    if not text.strip():
        return []
    boundaries = {0, len(text)}
    for m in re.finditer(r"\n\s*\n+", text):
        boundaries.add(m.end())
    for m in _HEADING.finditer(text):
        boundaries.add(m.start())
    for m in _SENTENCE_BREAK.finditer(text):
        if not _ABBREVIATIONS.search(text[max(0, m.start() - 8) : m.start()]):
            boundaries.add(m.end())
    points = sorted(boundaries)
    candidates = []
    for left, right in zip(points, points[1:]):
        u = _clean_unit(text, left, right)
        if u is not None:
            candidates.append(u)

    # Combine short sentences until a heading/paragraph boundary or max_chars.
    # Keep an exact, contiguous source slice so all chars remain traceable.
    hard_breaks = {m.end() for m in re.finditer(r"\n\s*\n+", text)}
    hard_breaks.update(m.start() for m in _HEADING.finditer(text))
    out: list[Unit] = []
    pending: Unit | None = None
    for cand in candidates:
        can_merge = (
            pending is not None
            and cand.start not in hard_breaks
            and cand.end - pending.start <= max_chars
        )
        if can_merge:
            pending = _clean_unit(text, pending.start, cand.end)
        else:
            if pending is not None:
                out.extend(_split_oversized(text, pending, max_chars))
            pending = cand
    if pending is not None:
        out.extend(_split_oversized(text, pending, max_chars))
    return out


def _split_oversized(text: str, unit: Unit, limit: int) -> list[Unit]:
    if len(unit.text) <= limit:
        return [unit]
    result = []
    start = unit.start
    while unit.end - start > limit:
        upper = start + limit
        split = text.rfind(" ", start + limit // 2, upper)
        if split <= start:
            split = upper  # Extremely long token: the only forced hard split.
        if (piece := _clean_unit(text, start, split)) is not None:
            result.append(piece)
        start = split
        while start < unit.end and text[start].isspace():
            start += 1
    if (piece := _clean_unit(text, start, unit.end)) is not None:
        result.append(piece)
    return result


def request_items(text: str, units: list[Unit], *, think: bool = False) -> dict[str, Any]:
    """Build an exact HAL-X batch payload, no side effects."""
    if len(units) > MAX_UNITS_PER_REQUEST:
        raise ValueError("too many units for anonymous-tier one-minute batch")
    items = []
    for unit in units:
        items.append(
            {
                "state": {
                    "trecho": unit.text,
                    "anterior": text[max(0, unit.start - 200) : unit.start],
                    "posterior": text[unit.end : unit.end + 200],
                },
                "questions": {
                    "papel": {
                        "type": "choice",
                        "instructions": (
                            "Classifique o PAPEL DO TRECHO no documento judicial brasileiro. "
                            "Considere o que o trecho faz agora, não palavras citadas "
                            "sobre decisões anteriores. Escolha 'outro' se misto ou incerto."
                        ),
                        "criteria": ROLES,
                    }
                },
                "think": think,
                "tta": 1,
            }
        )
    return {"model": "thx-02", "items": items}


def parse_results(units: list[Unit], result: dict, *, threshold: float = 0.80) -> list[Prediction]:
    """Fail closed on mismatched/missing results, bad labels or probabilities."""
    records = result.get("results")
    if not isinstance(records, list) or len(records) != len(units):
        raise ValueError("THX batch returned an unexpected number of results")
    predictions = []
    for unit, record in zip(units, records, strict=True):
        answers = record.get("answers") if isinstance(record, dict) else None
        answer = answers.get("papel", {}) if isinstance(answers, dict) else {}
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            predictions.append(Prediction(unit.start, unit.end, "unknown", 0, "unavailable"))
            continue
        label = answer.get("choice")
        probabilities = answer.get("probabilities")
        p = probabilities.get(label) if isinstance(probabilities, dict) else None
        valid_dist = (
            isinstance(probabilities, dict)
            and set(probabilities) == set(ROLES)
            and all(type(v) in (int, float) and 0 <= v <= 1 for v in probabilities.values())
            and abs(sum(probabilities.values()) - 1) <= 0.03
        )
        if label not in ROLES or not valid_dist or isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
            predictions.append(Prediction(unit.start, unit.end, "unknown", 0, "unavailable"))
            continue
        accepted = p >= threshold and label != "outro"
        predictions.append(
            Prediction(
                unit.start,
                unit.end,
                label if accepted else "unknown",
                float(p),
                "accepted" if accepted else "abstained",
            )
        )
    return predictions


def merge_regions(predictions: list[Prediction]) -> list[dict]:
    """Merge consecutive *accepted* units of one role, without inventing offsets."""
    regions: list[dict] = []
    merge_allowed = False
    for item in predictions:
        if item.status != "accepted":
            merge_allowed = False
            continue
        if merge_allowed and regions and regions[-1]["label"] == item.label and regions[-1]["end"] <= item.start:
            regions[-1]["end"] = item.end
            regions[-1]["unit_count"] += 1
            regions[-1]["min_probability"] = min(regions[-1]["min_probability"], item.probability)
        else:
            regions.append(
                {
                    "label": item.label,
                    "start": item.start,
                    "end": item.end,
                    "min_probability": item.probability,
                    "unit_count": 1,
                }
            )
        merge_allowed = True
    return regions


def boundary_ceiling(documents: list[dict], *, max_chars: int = 600, tolerance: int = 60) -> dict:
    """Pure preprocessing ceiling using train/val *if explicitly supplied*.

    This is NOT THX quality. Measure how often a gold structural boundary could
    be reproduced by our unit cutter, before the classifier is ever invoked.
    Excludes short within-section value/resultado anchors by design.
    """
    total = matched = 0
    misses: dict[str, int] = {}
    counts = []
    for doc in documents:
        text = doc["text"]
        units = split_units(text, max_chars=max_chars)
        counts.append(len(units))
        edges = [u.start for u in units] + [u.end for u in units]
        for span in doc.get("label", []):
            cat = span["category"]
            if not (cat.endswith("_inicio") or cat.endswith("_fim") or cat == "dispositivo_abertura"):
                continue
            total += 1
            boundary = int(span["start"] if cat.endswith("_inicio") or cat == "dispositivo_abertura" else span["end"])
            if edges and min(abs(boundary - b) for b in edges) <= tolerance:
                matched += 1
            else:
                misses[cat] = misses.get(cat, 0) + 1
    return {
        "documents": len(documents),
        "units": sum(counts),
        "mean_units_per_document": round(sum(counts) / len(counts), 2) if counts else None,
        "boundaries_within_tolerance": matched,
        "gold_structural_boundaries": total,
        "ceiling_recall": round(matched / total, 4) if total else None,
        "tolerance_chars": tolerance,
        "misses_by_class": misses,
        "interpretation": "preprocessing-only boundary ceiling; not THX inference or F1",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=Path("tests/fixtures/thx02_segmenter_synthetic.jsonl"))
    parser.add_argument("--audit-train", type=Path, help="Train/development JSONL only; never final test")
    parser.add_argument("--live", action="store_true", help="Actually transmit the provided document")
    parser.add_argument("--allow-public-documents", action="store_true", help="Explicit opt-in for live non-fixture documents")
    parser.add_argument("--output", type=Path, help="Write JSONL results; default stdout")
    parser.add_argument("--max-chars", type=int, default=600)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--max-units", type=int, default=40)
    args = parser.parse_args()
    if not 0 < args.threshold <= 1 or not 1 <= args.max_units <= MAX_UNITS_PER_REQUEST:
        parser.error("threshold must be (0,1]; max-units must be 1..60")
    if args.audit_train is not None:
        docs = [json.loads(line) for line in args.audit_train.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(json.dumps(boundary_ceiling(docs, max_chars=args.max_chars), ensure_ascii=False, indent=2))
        return 0
    if args.live and args.source.resolve() != Path("tests/fixtures/thx02_segmenter_synthetic.jsonl").resolve() and not args.allow_public_documents:
        parser.error("--live with a custom source requires --allow-public-documents (no sensitive texts)")
    if not args.source.exists():
        parser.error(f"source not found: {args.source}")
    docs = [json.loads(line) for line in args.source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(docs) != 1:
        parser.error("spike accepts exactly one document to avoid exceeding free-tier quotas")
    doc = docs[0]
    text = doc["text"]
    units = split_units(text, max_chars=args.max_chars)
    if len(units) > args.max_units:
        parser.error(f"{len(units)} units exceed --max-units {args.max_units}; provide a smaller document")
    payload = request_items(text, units)
    predictions = []
    if args.live and units:
        headers = {"Content-Type": "application/json"}
        if key := os.environ.get("HALX_API_KEY"):
            headers["Authorization"] = f"Bearer {key}"
        with httpx.Client(timeout=120) as client:
            response = client.post(ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            predictions = parse_results(units, response.json(), threshold=args.threshold)
    output = {
        "document_id": doc.get("id"),
        "model": "thx-02",
        "live": bool(args.live),
        "units": [asdict(u) for u in units],
        "predictions": [asdict(p) for p in predictions],
        "regions": merge_regions(predictions),
        "decisions_requested": len(units),
        "transmitted": bool(args.live and units),
    }
    data = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(data + "\n", encoding="utf-8")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())