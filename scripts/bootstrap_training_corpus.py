#!/usr/bin/env python3
r"""Bootstrap high-quality training corpus using OPF base model + agent review.

Two-stage pipeline (can run independently):
  Stage 1 (CPU/GPU): OPF detects entities, heuristic detects sections, auto-maps
    unambiguous labels → saves intermediate.jsonl with person spans for review
  Stage 2 (agents): Claude agents review person spans, classify roles, produce
    final v5 training corpus

Stage 1 runs via GHA (bootstrap-corpus.yml) or locally:
    python scripts/bootstrap_training_corpus.py \
        --input data/texts.jsonl --device -1 \
        --save-intermediate data/intermediate.jsonl

Stage 2 (agent review) loads intermediate and merges:
    python scripts/bootstrap_training_corpus.py \
        --load-intermediate data/intermediate.jsonl \
        --output-dir models/decision_segmenter

Full pipeline (Colab with GPU + API key):
    python scripts/bootstrap_training_corpus.py \
        --input data/texts.jsonl --device 0 \
        --output-dir models/decision_segmenter
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import structlog

from scripts.prepare_privacy_filter_dataset import LABEL_SPACE_V5, _segment


logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# OPF v2 → CausaGanha v5 auto-mapping (no LLM needed)
# ---------------------------------------------------------------------------

AUTO_MAP: dict[str, str] = {
    "private_email": "email",
    "private_phone": "telefone",
    "private_address": "endereco",
    "private_date": "data",
    "private_url": "O",
    "secret": "O",
}

# Account numbers are regex-classified, not sent to Haiku
_CPF_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
_OAB_CONTEXT_RE = re.compile(r"OAB", re.IGNORECASE)

# Labels that need Haiku reclassification
HAIKU_LABELS = frozenset({"private_person"})

PERSON_TARGET_LABELS = [
    "parte_autor",
    "parte_reu",
    "nome_advogado",
    "autoridade_judicial",
    "O",
]

CONTEXT_CHARS = 150


# ---------------------------------------------------------------------------
# Stage 1: OPF base model inference
# ---------------------------------------------------------------------------


def run_opf_inference(texts: list[str], *, device: int = -1) -> list[list[dict]]:
    """Run OPF base model on texts, return spans per text.

    Each span: {"label": str, "start": int, "end": int, "text": str}
    Uses OPF's native Python API (opf._api.OPF) instead of HuggingFace pipeline.
    """
    from opf._api import OPF  # noqa: PLC0415

    device_str = "cpu" if device < 0 else "cuda"
    logger.info("loading_opf_model", device=device_str)
    redactor = OPF(device=device_str, output_mode="typed")
    logger.info("opf_model_loaded")

    all_spans: list[list[dict]] = []
    for i, text in enumerate(texts):
        result = redactor.redact(text)
        parsed = [
            {
                "label": span.label,
                "start": span.start,
                "end": span.end,
                "text": span.text,
            }
            for span in result.detected_spans
        ]
        all_spans.append(parsed)
        done = i + 1
        if done % 50 == 0 or done == len(texts):
            logger.info("opf_progress", done=done, total=len(texts))

    return all_spans


# ---------------------------------------------------------------------------
# Stage 1.5: Auto-map unambiguous labels + regex-classify accounts
# ---------------------------------------------------------------------------


def classify_account(span_text: str, context_before: str) -> str:
    """Regex-classify an account_number span into cpf_cnpj/oab/processo_cnj."""
    if _CNJ_RE.search(span_text):
        return "processo_cnj"
    if _CPF_RE.search(span_text) or _CNPJ_RE.search(span_text):
        return "cpf_cnpj"
    if _OAB_CONTEXT_RE.search(context_before[-80:]) or _OAB_CONTEXT_RE.search(span_text):
        return "oab"
    if re.search(r"CPF|CNPJ", context_before[-80:], re.IGNORECASE):
        return "cpf_cnpj"
    return "O"


def auto_map_spans(text: str, opf_spans: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split OPF spans into auto-mapped (resolved) and ambiguous (need Haiku).

    Returns (resolved_spans, ambiguous_spans).
    Each span dict gets a "label" field added.
    """
    resolved = []
    ambiguous = []

    for span in opf_spans:
        opf_label = span["label"]
        s, e = span["start"], span["end"]
        span_text = span.get("text", text[s:e])

        if opf_label in AUTO_MAP:
            label = AUTO_MAP[opf_label]
            if label != "O":
                resolved.append({"start": s, "end": e, "label": label, "text": span_text})
        elif opf_label == "account_number":
            ctx_before = text[max(0, s - 80) : s]
            label = classify_account(span_text, ctx_before)
            resolved.append({"start": s, "end": e, "label": label, "text": span_text})
        elif opf_label in HAIKU_LABELS:
            ctx_before = text[max(0, s - CONTEXT_CHARS) : s]
            ctx_after = text[e : e + CONTEXT_CHARS]
            ambiguous.append(
                {
                    "start": s,
                    "end": e,
                    "text": span_text,
                    "opf_label": opf_label,
                    "context_before": ctx_before,
                    "context_after": ctx_after,
                }
            )
        else:
            resolved.append({"start": s, "end": e, "label": "O", "text": span_text})

    return resolved, ambiguous


# ---------------------------------------------------------------------------
# Stage 2: Haiku reclassification of person spans
# ---------------------------------------------------------------------------

_HAIKU_SYSTEM = """You classify person names detected in Brazilian judicial decisions.
Each span was detected by a privacy model as a person name. You assign the specific legal role.

Labels:
- parte_autor: plaintiff / active party (autor, requerente, exequente, apelante, reclamante)
- parte_reu: defendant / passive party (réu, requerido, executado, apelado, reclamado)
- nome_advogado: lawyer (advogado, procurador, near OAB registration)
- autoridade_judicial: judge, magistrate, or court clerk (juiz, desembargador, escrivão)
- O: not a relevant person (witness mentioned in text, generic reference, false positive)

Output ONLY valid JSON: {"<index>": "<label>", ...} for ALL spans. No explanation."""


def _build_haiku_prompt(spans: list[dict], section_hints: dict[int, str]) -> str:
    """Build a compact prompt listing indexed spans with context."""
    lines = []
    for i, sp in enumerate(spans):
        sec = section_hints.get(sp["start"], "unknown")
        ctx = f"...{sp['context_before']}[{sp['text']}]{sp['context_after']}..."
        ctx = ctx.replace("\n", " ")[:350]
        lines.append(f'[{i}] "{sp["text"]}" (section: {sec}) — {ctx}')
    return "\n".join(lines)


def _get_section_at(pos: int, section_spans: dict[str, list[list[int]]]) -> str:
    """Find which section a character position falls in."""
    for label, ranges in section_spans.items():
        for s, e in ranges:
            if s <= pos < e:
                return label
    return "unknown"


def call_haiku_batch(
    spans: list[dict],
    section_hints: dict[int, str],
    api_key: str,
    max_retries: int = 3,
) -> dict[str, str]:
    """Call Claude Haiku to classify person spans. Returns {index: label}."""
    import httpx  # noqa: PLC0415

    prompt = _build_haiku_prompt(spans, section_hints)

    for attempt in range(max_retries):
        try:
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "system": _HAIKU_SYSTEM,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(content)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("haiku_retry", attempt=attempt, error=str(exc))
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
    return {}


def classify_persons_haiku(
    texts: list[str],
    all_ambiguous: list[list[dict]],
    all_sections: list[dict[str, list[list[int]]]],
    api_key: str,
    batch_size: int = 40,
) -> list[list[dict]]:
    """Classify all ambiguous (person) spans via Haiku. Returns resolved spans per text."""
    results: list[list[dict]] = []
    total_spans = sum(len(a) for a in all_ambiguous)
    classified = 0

    for text_idx, (_text, ambiguous, sections) in enumerate(
        zip(texts, all_ambiguous, all_sections, strict=True)
    ):
        if not ambiguous:
            results.append([])
            continue

        section_hints = {sp["start"]: _get_section_at(sp["start"], sections) for sp in ambiguous}

        resolved_for_text = []
        for i in range(0, len(ambiguous), batch_size):
            batch = ambiguous[i : i + batch_size]
            labels = call_haiku_batch(batch, section_hints, api_key)

            for j, sp in enumerate(batch):
                label = labels.get(str(j), "O")
                if label not in PERSON_TARGET_LABELS:
                    label = "O"
                if label != "O":
                    resolved_for_text.append(
                        {"start": sp["start"], "end": sp["end"], "label": label}
                    )

            classified += len(batch)

        results.append(resolved_for_text)

        if (text_idx + 1) % 50 == 0 or text_idx + 1 == len(texts):
            logger.info(
                "haiku_progress",
                texts_done=text_idx + 1,
                spans_classified=classified,
                total_spans=total_spans,
            )

    return results


# ---------------------------------------------------------------------------
# Merge all label sources into OPF training format
# ---------------------------------------------------------------------------


def merge_spans(
    heuristic: dict[str, list[list[int]]],
    auto_mapped: list[dict],
    haiku_classified: list[dict],
) -> dict[str, list[list[int]]]:
    """Merge heuristic sections + OPF auto-mapped + Haiku-classified into final spans.

    Entity spans (from OPF/Haiku) take priority over section spans when overlapping.
    """
    spans: dict[str, list[list[int]]] = {}

    # Start with heuristic sections
    for label, ranges in heuristic.items():
        if label.startswith("sec_"):
            spans[label] = [list(r) for r in ranges]

    # Add heuristic entity labels (id_lei, valor_monetario, etc.)
    for label, ranges in heuristic.items():
        if not label.startswith("sec_"):
            spans.setdefault(label, []).extend([list(r) for r in ranges])

    # Add OPF auto-mapped entities
    for sp in auto_mapped:
        spans.setdefault(sp["label"], []).append([sp["start"], sp["end"]])

    # Add Haiku-classified persons
    for sp in haiku_classified:
        spans.setdefault(sp["label"], []).append([sp["start"], sp["end"]])

    return spans


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def load_texts(input_path: Path, limit: int | None = None) -> list[dict]:
    """Load texts from parquet or JSONL. Returns list of {"id": str, "texto": str}."""
    rows: list[dict] = []

    if input_path.suffix == ".jsonl":
        with input_path.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                texto = (rec.get("text") or rec.get("texto") or "").strip()
                if len(texto) >= 200:
                    uid = rec.get("id", str(hash(texto[:200])))
                    rows.append({"id": str(uid), "texto": texto})
    else:
        import ibis  # noqa: PLC0415

        t = ibis.read_parquet(input_path)
        col = "texto" if "texto" in t.columns else "text"
        df = t.filter(t[col].notnull()).execute()
        for _, row in df.iterrows():
            texto = (row.get("texto") or row.get("text") or "").strip()
            if len(texto) >= 200:
                uid = row.get("id", row.get("text_uuid", str(hash(texto[:200]))))
                rows.append({"id": str(uid), "texto": texto})

    if limit:
        rows = rows[:limit]
    logger.info("texts_loaded", count=len(rows), source=str(input_path))
    return rows


def _merge_and_write(
    texts: list[str],
    all_heuristic: list[dict],
    all_auto: list[list[dict]],
    all_haiku: list[list[dict]],
    args: argparse.Namespace,
) -> int:
    """Merge all label sources, split, and write training JSONL."""
    from collections import Counter  # noqa: PLC0415

    logger.info("merging_labels")
    records: list[dict] = []
    for text, heur, auto, haiku in zip(texts, all_heuristic, all_auto, all_haiku, strict=True):
        merged = merge_spans(heur, auto, haiku)
        if not merged:
            continue
        has_section = any(k.startswith("sec_") for k in merged)
        has_entity = any(not k.startswith("sec_") for k in merged)
        if has_section or has_entity:
            records.append({"text": text, "spans": merged})

    logger.info("records_built", count=len(records))

    random.shuffle(records)
    n = len(records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    splits = {
        "train": records[:train_end],
        "val": records[train_end:val_end],
        "test": records[val_end:],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, recs in splits.items():
        path = args.output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.info("jsonl_written", split=name, path=str(path), count=len(recs))

    label_space_path = args.output_dir / "label_space.json"
    label_space_path.write_text(
        json.dumps(LABEL_SPACE_V5, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    label_counts: Counter[str] = Counter()
    for rec in records:
        for label in rec["spans"]:
            label_counts[label] += 1

    print(f"\n{'=' * 60}")
    print("BOOTSTRAP CORPUS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total records: {len(records)}")
    print(f"Train/Val/Test: {len(splits['train'])}/{len(splits['val'])}/{len(splits['test'])}")
    print("\nLabel coverage:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        pct = count / len(records) * 100
        print(f"  {label:<22} {count:>5} ({pct:.1f}%)")
    print(f"{'=' * 60}")

    return 0


def _run_from_intermediate(args: argparse.Namespace) -> int:
    """Stage 2 only: load intermediate JSONL, run Haiku, merge, write output."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.skip_haiku:
        logger.error("ANTHROPIC_API_KEY not set. Use --skip-haiku for heuristic-only merge.")
        return 1

    logger.info("loading_intermediate", path=str(args.load_intermediate))
    with args.load_intermediate.open(encoding="utf-8") as f:
        records_raw = [json.loads(line) for line in f if line.strip()]
    logger.info("intermediate_loaded", count=len(records_raw))

    if len(records_raw) < 10:
        logger.error("insufficient_records", count=len(records_raw))
        return 1

    texts = [r["text"] for r in records_raw]
    all_heuristic = [r["heuristic_spans"] for r in records_raw]
    all_auto = [r["auto_mapped"] for r in records_raw]
    all_ambiguous = [r["ambiguous"] for r in records_raw]

    total_ambig = sum(len(a) for a in all_ambiguous)
    logger.info("intermediate_stats", texts=len(texts), need_haiku=total_ambig)

    if args.skip_haiku or not api_key:
        logger.info("skipping_haiku")
        all_haiku: list[list[dict]] = [[] for _ in texts]
    else:
        logger.info("stage2_haiku", total_persons=total_ambig)
        all_haiku = classify_persons_haiku(
            texts,
            all_ambiguous,
            all_heuristic,
            api_key,
            batch_size=args.haiku_batch_size,
        )
        haiku_classified = sum(len(h) for h in all_haiku)
        dropped = total_ambig - haiku_classified
        logger.info("haiku_done", classified=haiku_classified, dropped_as_O=dropped)

    return _merge_and_write(texts, all_heuristic, all_auto, all_haiku, args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap training corpus via OPF + Haiku")
    parser.add_argument("--input", type=Path, help="Input texts (parquet or JSONL)")
    parser.add_argument("--output-dir", type=Path, default=Path("models/decision_segmenter"))
    parser.add_argument("--target", type=int, default=2000, help="Max texts to process")
    parser.add_argument("--haiku-batch-size", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=int, default=-1, help="Device for OPF (-1=CPU, 0+=GPU)")
    parser.add_argument(
        "--skip-haiku",
        action="store_true",
        help="Skip Haiku step (use only auto-mapped + heuristic labels)",
    )
    stage_group = parser.add_mutually_exclusive_group()
    stage_group.add_argument(
        "--save-intermediate",
        type=Path,
        metavar="PATH",
        help="Run stages 1/1b/1.5 only and save intermediate JSONL (no Haiku)",
    )
    stage_group.add_argument(
        "--load-intermediate",
        type=Path,
        metavar="PATH",
        help="Skip OPF, load intermediate JSONL, run Haiku + merge",
    )
    args = parser.parse_args()

    random.seed(args.seed)

    if args.load_intermediate:
        return _run_from_intermediate(args)

    if not args.input:
        parser.error("--input is required unless using --load-intermediate")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.skip_haiku and not args.save_intermediate:
        logger.error("ANTHROPIC_API_KEY not set. Use --skip-haiku or --save-intermediate.")
        return 1

    # --- Load texts ---
    rows = load_texts(args.input, limit=args.target)
    if len(rows) < 10:
        logger.error("insufficient_texts", count=len(rows))
        return 1

    texts = [r["texto"] for r in rows]

    # --- Stage 1: OPF inference ---
    logger.info("stage1_opf_inference", texts=len(texts), device=args.device)
    opf_spans_per_text = run_opf_inference(texts, device=args.device)

    opf_stats: dict[str, int] = {}
    for spans in opf_spans_per_text:
        for sp in spans:
            lbl = sp["label"]
            opf_stats[lbl] = opf_stats.get(lbl, 0) + 1
    logger.info("opf_detection_stats", **opf_stats)

    # --- Stage 1b: Heuristic sections + regex entities ---
    logger.info("stage1b_heuristic")
    all_heuristic: list[dict[str, list[list[int]]]] = []
    heuristic_ok = 0
    for text in texts:
        h = _segment(text)
        all_heuristic.append(h or {})
        if h:
            heuristic_ok += 1
    logger.info("heuristic_done", coverage=f"{heuristic_ok}/{len(texts)}")

    # --- Stage 1.5: Auto-map + split ambiguous ---
    logger.info("stage1_5_auto_map")
    all_auto: list[list[dict]] = []
    all_ambiguous: list[list[dict]] = []
    for text, opf_spans in zip(texts, opf_spans_per_text, strict=True):
        auto, ambig = auto_map_spans(text, opf_spans)
        all_auto.append(auto)
        all_ambiguous.append(ambig)

    total_auto = sum(len(a) for a in all_auto)
    total_ambig = sum(len(a) for a in all_ambiguous)
    logger.info("auto_map_done", auto_resolved=total_auto, need_haiku=total_ambig)

    # --- Save intermediate and exit if requested ---
    if args.save_intermediate:
        args.save_intermediate.parent.mkdir(parents=True, exist_ok=True)
        with args.save_intermediate.open("w", encoding="utf-8") as f:
            for row, heur, auto, ambig in zip(
                rows, all_heuristic, all_auto, all_ambiguous, strict=True
            ):
                f.write(
                    json.dumps(
                        {
                            "id": row["id"],
                            "text": row["texto"],
                            "heuristic_spans": heur,
                            "auto_mapped": auto,
                            "ambiguous": ambig,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        logger.info(
            "intermediate_saved",
            path=str(args.save_intermediate),
            count=len(rows),
            auto_mapped=total_auto,
            need_haiku=total_ambig,
        )
        return 0

    # --- Stage 2: Haiku reclassification ---
    if args.skip_haiku or not api_key:
        logger.info("skipping_haiku")
        all_haiku: list[list[dict]] = [[] for _ in texts]
    else:
        logger.info("stage2_haiku", total_persons=total_ambig)
        all_haiku = classify_persons_haiku(
            texts,
            all_ambiguous,
            all_heuristic,
            api_key,
            batch_size=args.haiku_batch_size,
        )
        haiku_classified = sum(len(h) for h in all_haiku)
        dropped = total_ambig - haiku_classified
        logger.info("haiku_done", classified=haiku_classified, dropped_as_O=dropped)

    return _merge_and_write(texts, all_heuristic, all_auto, all_haiku, args)


if __name__ == "__main__":
    sys.exit(main())
