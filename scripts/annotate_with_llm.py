#!/usr/bin/env python3
"""Annotate sampled judicial decisions with v7 anchor spans using LiteLLM.

Reads raw texts from sampled JSONL files, sends them to an LLM via LiteLLM
along with the annotation guidelines, validates offsets and overlap,
and splits the resulting annotated dataset into train/val/test splits.

The default mode (regex-anchored) asks the model to return a Python regex
pattern with a capturing group for each span. The script then resolves the
exact character offsets locally by running re.search() against the document
text. Use --legacy-offsets to revert to the old offset-based prompt.

Usage:
    export OPENROUTER_API_KEY="your-key"
    uv run python scripts/annotate_with_llm.py \
        --input-dir data/segmenter_samples \
        --model openrouter/google/gemma-3-27b-it:free \
        --limit 50

    # To use old offset-based mode:
    uv run python scripts/annotate_with_llm.py --legacy-offsets --limit 50
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import litellm
import structlog

from scripts.prepare_privacy_filter_dataset import (
    _stratified_split,
)


logger = structlog.get_logger()

# Enable model-specific optimizations if needed
litellm.drop_params = True

# Default char budget per batch (~80k chars ≈ 20k tokens for most models)
DEFAULT_BATCH_CHAR_BUDGET = 80_000

# Supported regex flag names
_FLAG_MAP = {
    "DOTALL": re.DOTALL,
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
}


def load_guidelines(path: Path) -> str:
    if not path.exists():
        msg = f"Guideline file not found: {path}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def load_label_space(path: Path) -> dict:
    if not path.exists():
        msg = f"Label space file not found: {path}"
        raise FileNotFoundError(msg)
    return json.loads(path.read_text(encoding="utf-8"))


def load_raw_samples(input_dir: Path, limit: int | None = None) -> list[dict]:
    files = list(input_dir.glob("*.jsonl"))
    records = []
    for f in files:
        if "manifest" in f.name:
            continue
        with f.open(encoding="utf-8") as file:
            for line in file:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                rec = json.loads(stripped_line)
                # Keep raw text and info metadata
                records.append({"text": rec["text"], "info": rec.get("info", {})})

    # Shuffle and limit
    random.Random(42).shuffle(records)
    if limit is not None:
        records = records[:limit]

    logger.info("loaded_raw_samples", count=len(records), files=len(files))
    return records


def build_batches(
    records: list[dict],
    char_budget: int = DEFAULT_BATCH_CHAR_BUDGET,
) -> list[list[dict]]:
    """Greedily pack records into batches that fit within char_budget."""
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_size = 0
    for rec in records:
        size = len(rec["text"])
        if current and current_size + size > char_budget:
            batches.append(current)
            current = []
            current_size = 0
        current.append(rec)
        current_size += size
    if current:
        batches.append(current)
    logger.info("batches_built", total_batches=len(batches), total_records=len(records))
    return batches


def resolve_regex_spans(
    raw_spans: list[dict],
    text: str,
    valid_categories: set[str],
) -> list[dict]:
    """Resolve regex-anchored spans to (start, end) offsets.

    Each raw span must have:
      - category: str
      - pattern: str  (Python re-compatible; the span is in a capturing group)
      - group: int    (1-indexed capturing group that contains the span text)
      - flags: list[str]  optional, from ["DOTALL", "IGNORECASE", "MULTILINE"]

    Returns a list of {category, start, end} dicts ready for clean_and_validate_spans.
    """
    resolved: list[dict] = []
    for sp in raw_spans:
        cat = sp.get("category")
        pattern_str = sp.get("pattern")
        group_idx = sp.get("group", 1)
        flag_names = sp.get("flags") or []

        if not cat or not pattern_str:
            logger.warning("regex_span_missing_fields", span=sp)
            continue

        if cat not in valid_categories:
            logger.warning("invalid_category_ignored", category=cat)
            continue

        # Build combined flags
        flags = 0
        for name in flag_names:
            flag = _FLAG_MAP.get(name.upper())
            if flag is None:
                logger.warning("unknown_regex_flag", flag=name, category=cat)
            else:
                flags |= flag

        # Compile and run the pattern
        try:
            compiled = re.compile(pattern_str, flags)
        except re.error as exc:
            logger.warning(
                "regex_compile_failed",
                category=cat,
                pattern=pattern_str,
                error=str(exc),
            )
            continue

        # The prompt requires each pattern to match exactly once. A pattern
        # that matches multiple times is ambiguous — judicial anchors like
        # "Ante o exposto" can appear in quoted precedent before the operative
        # occurrence — so silently taking the first hit would plant a
        # valid-looking but wrong offset. Reject it for manual review instead.
        matches = list(compiled.finditer(text))
        if not matches:
            logger.warning("regex_no_match", category=cat, pattern=pattern_str[:80])
            continue
        if len(matches) > 1:
            logger.warning(
                "regex_ambiguous_match",
                category=cat,
                pattern=pattern_str[:80],
                n_matches=len(matches),
            )
            continue
        match = matches[0]

        try:
            start, end = match.span(group_idx)
        except IndexError:
            logger.warning(
                "regex_group_out_of_range",
                category=cat,
                group=group_idx,
                n_groups=compiled.groups,
            )
            continue

        if start >= end:
            logger.warning("regex_empty_span", category=cat, start=start, end=end)
            continue

        logger.info("regex_resolved", category=cat, start=start, end=end)
        resolved.append({"category": cat, "start": start, "end": end})

    return resolved


def clean_and_validate_spans(
    spans: list[dict],
    text: str,
    valid_categories: set[str],
) -> list[dict]:
    """Validate offsets, trim whitespace, remove duplicates/overlaps, check categories."""
    cleaned = []
    text_len = len(text)

    for sp in spans:
        cat = sp.get("category")
        start = sp.get("start")
        end = sp.get("end")

        if not cat or start is None or end is None:
            continue

        try:
            start = int(start)
            end = int(end)
        except (ValueError, TypeError):
            logger.warning("invalid_offset_type_ignored", category=cat, start=start, end=end)
            continue

        if cat not in valid_categories:
            logger.warning("invalid_category_ignored", category=cat)
            continue

        if not (0 <= start < end <= text_len):
            logger.warning(
                "out_of_bounds_offsets_ignored",
                category=cat,
                start=start,
                end=end,
                text_len=text_len,
            )
            continue

        # Verify matched text if provided
        expected_surface = text[start:end]
        actual_surface = sp.get("text")
        if actual_surface and actual_surface.strip() != expected_surface.strip():
            # Auto-recovery: find occurrences of the actual surface text in the document
            # If it occurs exactly once, we use that offset!
            occurrences = [m.start() for m in re.finditer(re.escape(actual_surface.strip()), text)]
            if len(occurrences) == 1:
                start = occurrences[0]
                end = start + len(actual_surface.strip())
                expected_surface = text[start:end]
                logger.info("offset_recovered_via_text", category=cat, text=actual_surface.strip())
            else:
                # Try finding it relative to the suggested start offset
                # (e.g. within a window of 200 characters around start)
                best_idx = -1
                best_dist = float("inf")
                for occ in occurrences:
                    dist = abs(occ - start)
                    if dist < best_dist and dist < 200:
                        best_dist = dist
                        best_idx = occ
                if best_idx != -1:
                    start = best_idx
                    end = start + len(actual_surface.strip())
                    expected_surface = text[start:end]
                    logger.info(
                        "offset_recovered_near_guess",
                        category=cat,
                        text=actual_surface.strip(),
                        dist=best_dist,
                    )
                else:
                    logger.warning(
                        "surface_mismatch_ignored",
                        category=cat,
                        expected=expected_surface,
                        actual=actual_surface,
                    )
                    continue

        # Trim whitespace from offsets
        surface = text[start:end]
        trimmed = surface.strip()
        if trimmed and trimmed != surface:
            start += surface.index(trimmed)
            end = start + len(trimmed)

        if start < end:
            cleaned.append({"category": cat, "start": int(start), "end": int(end)})

    # Remove duplicates
    seen = set()
    deduped = []
    for sp in cleaned:
        key = (sp["category"], sp["start"], sp["end"])
        if key not in seen:
            seen.add(key)
            deduped.append(sp)

    # Resolve overlaps: sort by start ascending, then duration descending
    deduped.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    non_overlapping = []
    last_end = -1
    for sp in deduped:
        if sp["start"] >= last_end:
            non_overlapping.append(sp)
            last_end = sp["end"]
        else:
            logger.warning(
                "overlapping_span_dropped",
                category=sp["category"],
                range=(sp["start"], sp["end"]),
            )

    return non_overlapping


def _build_system_prompt_regex(guidelines: str, label_space: list[str]) -> str:
    """System prompt for regex-anchored span annotation (default mode)."""
    return (
        "You are an expert legal annotator for Brazilian judicial decisions.\n"
        "Your task is to identify and extract anchor spans based on strict guidelines.\n\n"
        "### Guidelines:\n"
        f"{guidelines}\n\n"
        "### Valid Span Categories:\n"
        f"{label_space}\n\n"
        "### Output Format:\n"
        "You will be given one or more documents separated by markers. "
        "For EACH document, return a JSON object with:\n"
        '  - "doc_id": the exact ID from the document marker\n'
        '  - "spans": a list of span objects, each with:\n'
        '      - "category": one of the valid span categories listed above\n'
        '      - "pattern": a Python re-compatible regex string. '
        "The actual span text MUST be inside a capturing group (...).\n"
        '      - "group": the 1-indexed capturing group number that contains the span\n'
        '      - "flags": optional list of regex flags to apply, chosen from '
        '["DOTALL", "IGNORECASE", "MULTILINE"]. Use DOTALL for multi-line spans.\n\n'
        "CRITICAL RULES:\n"
        "1. Use enough surrounding context in the pattern to make the match UNIQUE "
        "within the document. If the span text could appear multiple times, "
        "include distinctive context before/after it in the pattern.\n"
        "2. Escape all regex special characters that appear literally in the text "
        "(e.g., . ( ) [ ] * + ? ^ $ | \\ must be escaped as \\. \\( etc.).\n"
        "3. The capturing group must match the span text EXACTLY (no leading/trailing spaces).\n"
        "4. Wrap ALL results in a top-level JSON array — one object per document.\n"
        "5. Do not include markdown, explanation text, or triple backticks. "
        "Just return the JSON array."
    )


def _build_system_prompt_legacy(guidelines: str, label_space: list[str]) -> str:
    """System prompt for legacy offset-based annotation."""
    return (
        "You are an expert legal annotator for Brazilian judicial decisions.\n"
        "Your task is to identify and extract anchor spans based on strict guidelines.\n\n"
        "### Guidelines:\n"
        f"{guidelines}\n\n"
        "### Valid Span Categories:\n"
        f"{label_space}\n\n"
        "### Output Format:\n"
        "You MUST respond ONLY with a valid JSON array of objects representing "
        "the identified spans, formatted exactly as:\n"
        '[\n  {"category": "category_name", "start": 100, "end": 115, '
        '"text": "matched text"}\n]\n'
        "Offsets must be 0-indexed character indices (UTF-8 codepoints) "
        "in the text, end-exclusive.\n"
        "Ensure there are no overlapping spans, and that every `text` "
        "matches exactly `decision_text[start:end]`.\n"
        "Do not include markdown blocks, explanation text, or triple backticks. "
        "Just return the JSON array."
    )


def _parse_llm_json(content: str) -> object:
    """Strip markdown fences and extract JSON from LLM response."""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try finding array or object inside surrounding text
        match = re.search(r"[\[\{].*[\]\}]", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def annotate_batch(
    batch: list[dict],
    guidelines: str,
    label_space: list[str],
    model: str,
) -> dict[str, list[dict]]:
    """Annotate a batch of documents using regex-anchored span extraction.

    Args:
        batch: list of {"doc_id": str, "text": str} dicts
        guidelines: annotation guidelines string
        label_space: list of valid category names
        model: LiteLLM model identifier

    Returns:
        dict mapping doc_id -> list of raw span dicts
        (each span has category, pattern, group, flags)
    """
    system_prompt = _build_system_prompt_regex(guidelines, label_space)

    # Build user message: one block per document
    doc_blocks = [f"--- DOC {rec['doc_id']} ---\n{rec['text']}" for rec in batch]
    user_prompt = "\n\n".join(doc_blocks)

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content.strip()
        data = _parse_llm_json(content)

        # Expect a list of {doc_id, spans} objects
        if not isinstance(data, list):
            logger.error("batch_llm_invalid_format", raw=content[:300])
            return {}

        result: dict[str, list[dict]] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            doc_id = item.get("doc_id")
            spans = item.get("spans", [])
            if doc_id and isinstance(spans, list):
                result[str(doc_id)] = spans
        return result

    except Exception:
        logger.exception("batch_llm_annotation_failed")
        return {}


def annotate_text(
    text: str,
    guidelines: str,
    label_space: list[str],
    model: str,
) -> list[dict]:
    """Legacy single-document offset-based annotation (--legacy-offsets mode)."""
    system_prompt = _build_system_prompt_legacy(guidelines, label_space)
    user_prompt = f"### Decision Text to Annotate:\n{text}"

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format=(
                {"type": "json_object"}
                if "gemini" in model.lower() or "gpt" in model.lower()
                else None
            ),
        )
        content = response.choices[0].message.content.strip()
        data = _parse_llm_json(content)

        if isinstance(data, dict) and "spans" in data:
            data = data["spans"]
        if not isinstance(data, list):
            logger.error("llm_invalid_format", raw=content[:200])
            return []

        return data

    except Exception:
        logger.exception("llm_annotation_failed")
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate texts with v7 ontology using LiteLLM")
    parser.add_argument(
        "--input-dir",
        default="data/segmenter_samples",
        help="Directory with sampled JSONL files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/segmenter_splits",
        help="Directory to save gold splits",
    )
    parser.add_argument(
        "--model",
        default="openrouter/google/gemini-2.5-flash",
        help="LiteLLM model to use",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of decisions to annotate",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--legacy-offsets",
        action="store_true",
        help=(
            "Use old offset-based annotation (one doc per call) instead of regex-anchored batching"
        ),
    )
    parser.add_argument(
        "--batch-char-budget",
        type=int,
        default=DEFAULT_BATCH_CHAR_BUDGET,
        help="Max characters per batch in regex-anchored mode (default: %(default)s)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Override invalid/stale key in process environment with the latest key from root .env
    workspace_env = Path(__file__).resolve().parents[2] / ".env"
    if workspace_env.exists():
        correct_key = None
        for raw_line in workspace_env.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if "OPENROUTER_API_KEY" in line and "=" in line:
                val = line.split("=", 1)[1].strip("\"'")
                if val and val != "seu_token_aqui":
                    correct_key = val
        if correct_key:
            os.environ["OPENROUTER_API_KEY"] = correct_key

    # Check for keys
    if "openrouter" in args.model.lower() and not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is missing.", file=sys.stderr)
        return 1

    guidelines_path = output_dir / "annotation_guideline_v7.md"
    guidelines = load_guidelines(guidelines_path)

    label_space_path = output_dir / "label_space.json"
    ls_data = load_label_space(label_space_path)
    valid_categories = set(ls_data["span_class_names"])

    # Load approved models if they exist
    approved_models_path = output_dir / "approved_models.json"
    approved_models = []
    if approved_models_path.exists():
        try:
            approved_models = json.loads(approved_models_path.read_text(encoding="utf-8")).get(
                "approved_models", []
            )
        except Exception:
            logger.warning("failed_to_load_approved_models")

    # If default model was requested but we have approved models, use the top approved model
    if args.model == "openrouter/google/gemini-2.5-flash" and approved_models:
        args.model = approved_models[0]
        print(f"Automatically selected top approved model: {args.model}")
    elif approved_models and args.model not in approved_models:
        print(
            f"WARNING: The chosen model `{args.model}` is not in the approved models list. "
            f"It may be of low quality or failed the quality gate tests.",
            file=sys.stderr,
        )

    # Load raw sampled texts
    raw_records = load_raw_samples(input_dir, limit=args.limit)
    if not raw_records:
        logger.error("no_raw_samples_found", input_dir=str(input_dir))
        return 1

    annotated_records = []

    if args.legacy_offsets:
        # ── Legacy mode: one doc per call, offset-based ───────────────────────
        print(
            f"\n[LEGACY MODE] Starting offset-based annotation of {len(raw_records)} "
            f"decisions using {args.model}...\n"
        )
        for idx, rec in enumerate(raw_records, 1):
            text = rec["text"]
            doc_id = rec["info"].get("id", "unknown")
            print(f"[{idx}/{len(raw_records)}] Annotating document {doc_id} ({len(text)} chars)...")

            raw_spans = annotate_text(text, guidelines, list(valid_categories), args.model)
            cleaned_spans = clean_and_validate_spans(raw_spans, text, valid_categories)

            logger.info(
                "document_annotated",
                doc_id=doc_id,
                raw_spans=len(raw_spans),
                clean_spans=len(cleaned_spans),
            )
            annotated_records.append({"text": text, "label": cleaned_spans, "info": rec["info"]})

    else:
        # ── Regex-anchored batch mode (default) ───────────────────────────────
        # Prepare records with a locally-generated UNIQUE doc_id for batching.
        # Source ids (rec["info"]["id"]) may be empty or duplicated, which would
        # collapse distinct documents in the per-batch rec_by_id lookup and
        # misassign / silently drop annotations. The source id is preserved in
        # rec["info"]["id"] for provenance; the batch marker is always unique.
        for i, rec in enumerate(raw_records):
            rec["doc_id"] = f"doc_{i:06d}"

        batches = build_batches(raw_records, char_budget=args.batch_char_budget)
        print(
            f"\n[BATCH MODE] Annotating {len(raw_records)} decisions in "
            f"{len(batches)} batches using {args.model}...\n"
        )

        processed = 0
        for batch_idx, batch in enumerate(batches, 1):
            print(
                f"[Batch {batch_idx}/{len(batches)}] "
                f"{len(batch)} docs, "
                f"~{sum(len(r['text']) for r in batch):,} chars"
            )
            batch_input = [{"doc_id": r["doc_id"], "text": r["text"]} for r in batch]
            batch_result = annotate_batch(
                batch_input, guidelines, list(valid_categories), args.model
            )

            # Build lookup: doc_id -> original record
            rec_by_id = {r["doc_id"]: r for r in batch}

            for doc_id, raw_spans in batch_result.items():
                rec = rec_by_id.get(doc_id)
                if rec is None:
                    logger.warning("batch_unknown_doc_id", doc_id=doc_id)
                    continue

                text = rec["text"]

                # Resolve regex patterns to (start, end) offsets
                resolved = resolve_regex_spans(raw_spans, text, valid_categories)

                # Final overlap/bounds validation
                cleaned_spans = clean_and_validate_spans(resolved, text, valid_categories)

                logger.info(
                    "document_annotated",
                    doc_id=doc_id,
                    raw_spans=len(raw_spans),
                    resolved_spans=len(resolved),
                    clean_spans=len(cleaned_spans),
                )
                annotated_records.append(
                    {"text": text, "label": cleaned_spans, "info": rec["info"]}
                )
                processed += 1

            # Warn about docs the model silently skipped
            returned_ids = set(batch_result.keys())
            for rec in batch:
                if rec["doc_id"] not in returned_ids:
                    logger.warning("batch_doc_not_returned", doc_id=rec["doc_id"])

        print(f"\nBatch annotation complete. Resolved {processed}/{len(raw_records)} docs.")

    print(f"\nFinished annotation. Successfully annotated {len(annotated_records)} decisions.")

    # Perform stratified split
    print("Performing stratified train/val/test splitting...")
    splits = _stratified_split(annotated_records, seed=args.seed)

    # Save splits
    cat_counts: dict[str, int] = {}
    for name, data in splits.items():
        path = output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for rec in data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                for sp in rec["label"]:
                    cat_counts[sp["category"]] = cat_counts.get(sp["category"], 0) + 1
        logger.info("split_written", split=name, path=str(path), count=len(data))

    # Write manifest
    manifest = {
        "category_version": ls_data["category_version"],
        "seed": args.seed,
        "counts": {name: len(data) for name, data in splits.items()},
        "per_class": cat_counts,
        "test_verified_by": "llm_annotator",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest written to {manifest_path}")

    # Run format validation
    print("\nValidating outputs...")
    ok = True
    for split in ("train", "val", "test"):
        jsonl = output_dir / f"{split}.jsonl"
        cmd = [
            sys.executable,
            "scripts/opf_annotate.py",
            "validate",
            str(jsonl),
            "--label-space",
            str(label_space_path),
        ]
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"Validation FAILED for {split}.jsonl", file=sys.stderr)
            ok = False
        else:
            print(f"Validation PASSED for {split}.jsonl")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
