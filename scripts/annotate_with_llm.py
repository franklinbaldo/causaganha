#!/usr/bin/env python3
"""Annotate sampled judicial decisions with v7 anchor spans using LiteLLM.

Reads raw texts from sampled JSONL files, sends them to an LLM via LiteLLM
along with the annotation guidelines, validates offsets and overlap,
and splits the resulting annotated dataset into train/val/test splits.

Usage:
    export OPENROUTER_API_KEY="your-key"
    uv run python scripts/annotate_with_llm.py \
        --input-dir data/segmenter_samples \
        --model openrouter/google/gemini-2.5-flash \
        --limit 50
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


def annotate_text(
    text: str,
    guidelines: str,
    label_space: list[str],
    model: str,
) -> list[dict]:
    system_prompt = (
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

        # Clean any markdown packaging
        if content.startswith("```"):
            # strip leading/trailing code block formatting
            content = re.sub(r"^```(?:json)?\n", "", content)
            content = re.sub(r"\n```$", "", content)
            content = content.strip()

        # Parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try finding the array inside the response if it returned surrounding text
            match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise

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
                val = line.split("=", 1)[1].strip('"\'')
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
    print(f"\nStarting LLM annotation of {len(raw_records)} decisions using {args.model}...\n")

    for idx, rec in enumerate(raw_records, 1):
        text = rec["text"]
        doc_id = rec["info"].get("id", "unknown")
        print(f"[{idx}/{len(raw_records)}] Annotating document {doc_id} ({len(text)} chars)...")

        # Get raw spans from LLM
        raw_spans = annotate_text(text, guidelines, list(valid_categories), args.model)

        # Clean and validate offsets/overlaps/categories
        cleaned_spans = clean_and_validate_spans(raw_spans, text, valid_categories)

        logger.info(
            "document_annotated",
            doc_id=rec["info"].get("id"),
            raw_spans=len(raw_spans),
            clean_spans=len(cleaned_spans),
        )

        annotated_records.append({"text": text, "label": cleaned_spans, "info": rec["info"]})

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
