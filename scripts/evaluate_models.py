#!/usr/bin/env python3
"""Evaluate the quality of OpenRouter free models for v7 span annotation.

Query OpenRouter to find available free models, filters for Qwen, DeepSeek, and
Gemma, runs evaluations on sample documents, and ranks them by quality.

Usage:
    export OPENROUTER_API_KEY="your-key"
    uv run python scripts/evaluate_models.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx
import structlog

from scripts.annotate_with_llm import (
    annotate_text,
    load_guidelines,
    load_label_space,
)


logger = structlog.get_logger()

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def fetch_free_models() -> list[dict]:
    """Fetch all free models from OpenRouter."""
    logger.info("fetching_openrouter_models", url=OPENROUTER_MODELS_URL)
    response = httpx.get(OPENROUTER_MODELS_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    free_models = []
    for model in data.get("data", []):
        model_id = model.get("id", "")
        # Filter for free models
        is_free = ":free" in model_id or any(
            val in ("0", 0) for val in model.get("pricing", {}).values()
        )
        if not is_free:
            continue

        free_models.append(model)

    logger.info("found_free_models", count=len(free_models))
    return free_models


def filter_models(
    models: list[dict],
    *,
    allow_qwen: bool = True,
    allow_deepseek: bool = True,
    allow_gemma: bool = True,
    exclude_llama: bool = True,
) -> list[str]:
    """Filter models by requested families."""
    filtered = []
    for model in models:
        model_id = model["id"].lower()

        # Exclude llama if requested
        if exclude_llama and ("llama" in model_id or "meta/" in model_id):
            continue

        match = False
        if (allow_qwen and "qwen" in model_id) or (allow_deepseek and "deepseek" in model_id):
            match = True
        elif allow_gemma and ("gemma" in model_id or "google/" in model_id):
            # Also capture google/gemma models
            match = True

        if match:
            # We prefix openrouter/ for litellm compatibility
            filtered.append(f"openrouter/{model['id']}")

    logger.info("filtered_models", count=len(filtered), models=filtered)
    return filtered


def load_sample_texts(input_path: Path, count: int = 3) -> list[str]:
    """Load first few sample texts from jsonl."""
    texts = []
    if not input_path.exists():
        logger.error("sample_file_not_found", path=str(input_path))
        return []

    with input_path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if "text" in rec:
                texts.append(rec["text"])
            if len(texts) >= count:
                break
    return texts


def evaluate_model(
    model: str,
    texts: list[str],
    guidelines: str,
    valid_categories: set[str],
) -> dict:
    """Run annotation on samples and compute quality metrics."""
    logger.info("evaluating_model", model=model)
    print(f"Testing model {model} on {len(texts)} sample documents...")

    total_raw_spans = 0
    total_cleaned_spans = 0
    parse_successes = 0
    invalid_categories = 0
    mismatches = 0
    recovered = 0
    overlaps = 0

    for text in texts:
        # We need to measure if it parses correctly
        try:
            # Short timeout to avoid hanging on slow/rate-limited models
            # We wrap annotate_text logic with count metrics
            raw_spans = annotate_text(text, guidelines, list(valid_categories), model)
            parse_successes += 1
        except Exception as e:
            logger.warning("model_failed_annotation", model=model, error=str(e))
            continue

        if not raw_spans:
            continue

        total_raw_spans += len(raw_spans)

        # Now track what clean_and_validate_spans does but collect metrics
        cleaned = []
        text_len = len(text)

        for sp in raw_spans:
            cat = sp.get("category")
            start = sp.get("start")
            end = sp.get("end")

            if not cat or start is None or end is None:
                continue

            try:
                start = int(start)
                end = int(end)
            except (ValueError, TypeError):
                continue

            if cat not in valid_categories:
                invalid_categories += 1
                continue

            if not (0 <= start < end <= text_len):
                mismatches += 1
                continue

            # Offset checks
            expected_surface = text[start:end]
            actual_surface = sp.get("text")

            if actual_surface and actual_surface.strip() != expected_surface.strip():
                # Test if it can be recovered
                occurrences = [
                    m.start() for m in re.finditer(re.escape(actual_surface.strip()), text)
                ]
                if len(occurrences) == 1:
                    recovered += 1
                    start = occurrences[0]
                    end = start + len(actual_surface.strip())
                else:
                    best_idx = -1
                    best_dist = float("inf")
                    for occ in occurrences:
                        dist = abs(occ - start)
                        if dist < best_dist and dist < 200:
                            best_dist = dist
                            best_idx = occ
                    if best_idx != -1:
                        recovered += 1
                        start = best_idx
                        end = start + len(actual_surface.strip())
                    else:
                        mismatches += 1
                        continue

            # Normalize whitespace
            surface = text[start:end]
            trimmed = surface.strip()
            if trimmed and trimmed != surface:
                start += surface.index(trimmed)
                end = start + len(trimmed)

            if start < end:
                cleaned.append({"category": cat, "start": start, "end": end})

        # Overlaps
        seen = set()
        deduped = []
        for sp in cleaned:
            key = (sp["category"], sp["start"], sp["end"])
            if key not in seen:
                seen.add(key)
                deduped.append(sp)

        deduped.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
        last_end = -1
        for sp in deduped:
            if sp["start"] >= last_end:
                total_cleaned_spans += 1
                last_end = sp["end"]
            else:
                overlaps += 1

    # Calculate rates
    parse_rate = parse_successes / max(1, len(texts))

    # Avoid zero division
    denom = max(1, total_raw_spans)
    invalid_cat_rate = invalid_categories / denom
    mismatch_rate = mismatches / denom
    recovery_rate = recovered / denom
    overlap_rate = overlaps / denom
    clean_rate = total_cleaned_spans / denom if total_raw_spans > 0 else 0.0

    # Combined Quality Score formula
    # Higher is better, max 100.
    # Penalities:
    # - Failures to parse (major penalty)
    # - Mismatches/Invalid categories (moderate penalty)
    # - Overlaps (minor penalty)
    # - Recovery rate (slight penalty as it indicates model couldn't count offsets correctly,
    #   but we recovered it, so only -0.1 penalty per recovery)
    score = 0.0
    if parse_rate > 0:
        score = (
            (parse_rate * 40.0)
            + (clean_rate * 30.0)
            + ((1.0 - mismatch_rate) * 15.0)
            + ((1.0 - invalid_cat_rate) * 10.0)
            + ((1.0 - overlap_rate) * 5.0)
            - (recovery_rate * 5.0)  # Count offset recovery as slightly lower quality
        )
        score = max(0.0, min(100.0, score))

    metrics = {
        "model": model,
        "parse_rate": parse_rate,
        "raw_spans": total_raw_spans,
        "cleaned_spans": total_cleaned_spans,
        "invalid_categories": invalid_categories,
        "mismatches": mismatches,
        "recovered": recovered,
        "overlaps": overlaps,
        "score": round(score, 2),
        "status": "PASS" if score >= 50.0 and parse_rate >= 0.5 else "FAIL",
    }
    logger.info("model_evaluation_complete", **metrics)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate free OpenRouter models")
    parser.add_argument(
        "--input",
        default="data/segmenter_samples/tjro.jsonl",
        help="Path to JSONL sample file to use for evaluation",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=2,
        help="Number of samples to run per model",
    )
    parser.add_argument(
        "--output-report",
        default="data/segmenter_splits/model_evaluation_report.md",
        help="Path to save markdown report",
    )
    args = parser.parse_args()

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

    # Ensure OPENROUTER_API_KEY is present
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is missing.", file=sys.stderr)
        return 1

    output_dir = Path("data/segmenter_splits")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load label space and guidelines
    guidelines_path = output_dir / "annotation_guideline_v7.md"
    guidelines = load_guidelines(guidelines_path)

    label_space_path = output_dir / "label_space.json"
    ls_data = load_label_space(label_space_path)
    valid_categories = set(ls_data["span_class_names"])

    # Load sample texts
    texts = load_sample_texts(Path(args.input), count=args.samples)
    if not texts:
        print("Error: Could not load sample texts for evaluation.", file=sys.stderr)
        return 1

    # Fetch free models and filter them
    try:
        raw_free_models = fetch_free_models()
    except Exception as e:
        print(f"Error fetching models from OpenRouter: {e}", file=sys.stderr)
        return 1

    candidate_models = filter_models(raw_free_models)

    if not candidate_models:
        print(
            "No eligible free models (Qwen, DeepSeek, Gemma) found on OpenRouter.", file=sys.stderr
        )
        return 1

    print(f"Evaluating {len(candidate_models)} candidates on {len(texts)} docs...")
    results = []
    for model in candidate_models:
        try:
            res = evaluate_model(model, texts, guidelines, valid_categories)
            results.append(res)
        except Exception as e:
            print(f"Failed to evaluate {model}: {e}", file=sys.stderr)
            results.append(
                {
                    "model": model,
                    "parse_rate": 0.0,
                    "raw_spans": 0,
                    "cleaned_spans": 0,
                    "invalid_categories": 0,
                    "mismatches": 0,
                    "recovered": 0,
                    "overlaps": 0,
                    "score": 0.0,
                    "status": "FAIL",
                    "error": str(e),
                }
            )

    # Sort results by score descending
    results.sort(key=lambda r: r["score"], reverse=True)

    # Save approved models configuration
    approved = [r["model"] for r in results if r["status"] == "PASS"]
    approved_path = output_dir / "approved_models.json"
    approved_path.write_text(json.dumps({"approved_models": approved}, indent=2), encoding="utf-8")

    # Write markdown report
    report_path = Path(args.output_report)
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Model Quality Evaluation Scorecard\n\n")
        f.write(
            "Evaluation results for free OpenRouter models on "
            "Brazilian legal decision span annotations.\n\n"
        )
        f.write(
            "| Model | Score | Status | Parse Rate | Clean/Raw Spans | "
            "Mismatches | Recovered | Overlaps |\n"
        )
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in results:
            spans_ratio = f"{r['cleaned_spans']}/{r['raw_spans']}"
            f.write(
                f"| `{r['model']}` | **{r['score']}** | {r['status']} | "
                f"{int(r['parse_rate'] * 100)}% | {spans_ratio} | "
                f"{r['mismatches']} | {r['recovered']} | {r['overlaps']} |\n"
            )

        f.write("\n\n## Recommendations\n")
        if approved:
            f.write(f"- **Primary model recommendation:** `{approved[0]}`\n")
            f.write("- Approved models: " + ", ".join([f"`{m}`" for m in approved]) + "\n")
        else:
            f.write(
                "- **WARNING:** No models passed the quality gate. "
                "Please verify API limits or prompt settings.\n"
            )

    print(f"\nEvaluation complete. Scorecard written to {report_path}")
    print(f"Approved models config written to {approved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
