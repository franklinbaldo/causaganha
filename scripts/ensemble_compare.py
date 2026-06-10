#!/usr/bin/env python3
"""ensemble_compare.py — mechanical diff for verification-ensemble outputs.

Compares a reference annotation JSONL (the candidate gold) against one or
more role-output JSONLs (see data/segmenter_splits/verification_ensemble_v7.md)
and reports disagreements per document and per category:

    missing   — span in reference, absent from role output
    extra     — span in role output, absent from reference
    boundary  — same category overlapping region, different offsets
    category  — same offsets, different category

Exit code is non-zero while any disagreement remains, so this can gate the
"verified" status mechanically.

Usage:
    uv run python scripts/ensemble_compare.py reference.jsonl role_blind.jsonl
    uv run python scripts/ensemble_compare.py ref.jsonl r1.jsonl r2.jsonl r3.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for ln, raw in enumerate(fh, 1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as e:
                print(f"ERROR {path}:L{ln}: invalid JSON ({e})", file=sys.stderr)
                sys.exit(2)
    return records


def _spans_of(rec: dict) -> list[dict]:
    for field in ("label", "spans"):
        if field in rec:
            return rec[field] or []
    return []


def _key(sp: dict) -> tuple[str, int, int]:
    return (sp["category"], sp["start"], sp["end"])


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def compare_record(ref_spans: list[dict], role_spans: list[dict]) -> list[dict]:
    """Return the list of disagreements between reference and one role output."""
    ref_keys = {_key(sp) for sp in ref_spans}
    role_keys = {_key(sp) for sp in role_spans}
    disagreements: list[dict] = []

    for sp in ref_spans:
        if _key(sp) in role_keys:
            continue
        # exact offsets, different category?
        cat_clash = next(
            (r for r in role_spans if r["start"] == sp["start"] and r["end"] == sp["end"]),
            None,
        )
        if cat_clash is not None:
            disagreements.append(
                {
                    "kind": "category",
                    "category": sp["category"],
                    "other_category": cat_clash["category"],
                    "start": sp["start"],
                    "end": sp["end"],
                }
            )
            continue
        # same category, overlapping but shifted?
        boundary = next(
            (r for r in role_spans if r["category"] == sp["category"] and _overlaps(r, sp)),
            None,
        )
        if boundary is not None:
            disagreements.append(
                {
                    "kind": "boundary",
                    "category": sp["category"],
                    "start": sp["start"],
                    "end": sp["end"],
                    "other_start": boundary["start"],
                    "other_end": boundary["end"],
                }
            )
            continue
        disagreements.append(
            {
                "kind": "missing",
                "category": sp["category"],
                "start": sp["start"],
                "end": sp["end"],
            }
        )

    matched_in_ref = {
        _key(sp)
        for sp in role_spans
        if _key(sp) in ref_keys
        or any(r["start"] == sp["start"] and r["end"] == sp["end"] for r in ref_spans)
        or any(r["category"] == sp["category"] and _overlaps(r, sp) for r in ref_spans)
    }
    disagreements.extend(
        {
            "kind": "extra",
            "category": sp["category"],
            "start": sp["start"],
            "end": sp["end"],
        }
        for sp in role_spans
        if _key(sp) not in matched_in_ref
    )
    return disagreements


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("reference", help="Candidate gold JSONL")
    parser.add_argument("roles", nargs="+", help="Role output JSONL file(s)")
    parser.add_argument(
        "--context",
        type=int,
        default=40,
        help="Chars of text context to print around each disagreement",
    )
    args = parser.parse_args()

    ref = _load(Path(args.reference))
    total = 0
    per_category: dict[str, int] = {}

    for role_path_s in args.roles:
        role_path = Path(role_path_s)
        role = _load(role_path)
        if len(role) != len(ref):
            print(
                f"ERROR {role_path}: {len(role)} records, reference has {len(ref)} "
                f"(role outputs must keep record order)",
                file=sys.stderr,
            )
            return 2
        role_total = 0
        for i, (ref_rec, role_rec) in enumerate(zip(ref, role, strict=True)):
            text = ref_rec.get("text", "")
            disagreements = compare_record(_spans_of(ref_rec), _spans_of(role_rec))
            for d in disagreements:
                role_total += 1
                per_category[d["category"]] = per_category.get(d["category"], 0) + 1
                s, e = d["start"], d["end"]
                ctx_s = max(0, s - args.context)
                snippet = text[ctx_s : e + args.context].replace("\n", " ")
                doc_id = (ref_rec.get("info") or {}).get("id", f"doc{i}")
                detail = ""
                if d["kind"] == "category":
                    detail = f" role says [{d['other_category']}]"
                elif d["kind"] == "boundary":
                    detail = f" role says ({d['other_start']}:{d['other_end']})"
                print(
                    f"{role_path.name} {doc_id} {d['kind']:8s} "
                    f"[{d['category']}]({s}:{e}){detail}  ...{snippet}..."
                )
        print(f"-- {role_path.name}: {role_total} disagreement(s)", file=sys.stderr)
        total += role_total

    if per_category:
        print("\nper-category disagreements:", file=sys.stderr)
        for cat in sorted(per_category):
            print(f"  {cat}: {per_category[cat]}", file=sys.stderr)
    if total:
        print(f"\nFAILED: {total} disagreement(s) need adjudication", file=sys.stderr)
        return 1
    print("\nOK: ensemble agrees with reference", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
