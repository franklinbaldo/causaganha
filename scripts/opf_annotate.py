#!/usr/bin/env python3
"""opf_annotate.py — annotation helpers for fine-tuning OpenAI Privacy Filter (OPF).

The OPF trainer eats JSONL where each line is:
    {"text": str, "label": [{"category": str, "start": int, "end": int}], "info": {...}}
Offsets are CHARACTER offsets into `text`, start inclusive / end exclusive
(`text[start:end]` == span surface). Most annotation bugs are offset bugs, so this
tool exists mainly to catch them before you waste a training run.

Subcommands
-----------
  validate   Check a JSONL annotation file (offsets, overlaps, whitespace, UTF-8,
             optional label-space coverage). Exits non-zero on errors.
  from-spans Build OPF-schema JSONL from a looser input where spans may be given as
             a `match` substring (offsets computed for you) and/or explicit start/end.
  preview    Render spans inline in the terminal so you can eyeball boundaries.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import pairwise
from pathlib import Path


SPAN_FIELDS = ("label", "spans")


def _spans_of(rec: dict) -> list[dict]:
    for f in SPAN_FIELDS:
        if f in rec:
            return rec[f] or []
    return []


def _has_span_field(rec: dict) -> bool:
    return any(f in rec for f in SPAN_FIELDS)


def _read_jsonl(path: str):
    with Path(path).open(encoding="utf-8") as fh:
        for ln, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                yield ln, json.loads(line)
            except json.JSONDecodeError as e:
                yield ln, e


def _load_label_space(path: str) -> tuple[list[str], list[str]]:
    """Return (categories_without_O, problems)."""
    problems: list[str] = []
    with Path(path).open(encoding="utf-8") as fh:
        ls = json.load(fh)
    names = ls.get("span_class_names") or ls.get("category_names") or []
    if not names:
        problems.append("label space has no `span_class_names`")
    elif names[0] != "O":
        problems.append(f"`O` must be the first entry in span_class_names (got {names[0]!r})")
    return [n for n in names if n != "O"], problems


# --------------------------------------------------------------------------- validate
def validate(path: str, label_space: str | None) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    n_lines = 0
    n_spans = 0
    cat_counts: dict[str, int] = {}

    allowed: set[str] | None = None
    if label_space:
        cats, ls_problems = _load_label_space(label_space)
        errors.extend(f"[label-space] {p}" for p in ls_problems)
        allowed = set(cats)

    for ln, rec in _read_jsonl(path):
        if isinstance(rec, json.JSONDecodeError):
            errors.append(f"L{ln}: invalid JSON ({rec})")
            continue
        n_lines += 1
        text = rec.get("text")
        if not isinstance(text, str):
            errors.append(f"L{ln}: missing/invalid `text`")
            continue
        tlen = len(text)
        if not _has_span_field(rec):
            errors.append(f"L{ln}: record has no `label` or `spans` field")
            continue
        spans = _spans_of(rec)
        norm: list[tuple[int, int, str]] = []
        for i, sp in enumerate(spans):
            try:
                start, end, cat = sp["start"], sp["end"], sp["category"]
            except (KeyError, TypeError):
                errors.append(f"L{ln} span#{i}: needs start/end/category, got {sp!r}")
                continue
            if not (isinstance(start, int) and isinstance(end, int)):
                errors.append(f"L{ln} span#{i}: start/end must be ints (char offsets)")
                continue
            if not (0 <= start < end <= tlen):
                errors.append(
                    f"L{ln} span#{i} [{cat}]: bad offsets start={start} end={end} "
                    f"(text len={tlen}). Offsets are CHARACTER offsets, end-exclusive."
                )
                continue
            surface = text[start:end]
            if surface != surface.strip():
                warnings.append(
                    f"L{ln} span#{i} [{cat}]: leading/trailing whitespace in span "
                    f"-> {surface!r}. Trim before recording offsets."
                )
            if allowed is not None and cat not in allowed:
                errors.append(
                    f"L{ln} span#{i}: category {cat!r} not in label space ({sorted(allowed)})"
                )
            n_spans += 1
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            norm.append((start, end, cat))

        norm.sort()
        for (s1, e1, c1), (s2, e2, c2) in pairwise(norm):
            if s2 < e1:
                errors.append(
                    f"L{ln}: overlapping spans [{c1}]({s1}:{e1}) & [{c2}]({s2}:{e2}). "
                    f"BIOES allows one span per region."
                )

    print(f"lines: {n_lines}   spans: {n_spans}")
    if cat_counts:
        print("per-category:")
        for c in sorted(cat_counts):
            print(f"  {c}: {cat_counts[c]}")
        if allowed is not None:
            unused = sorted(allowed - set(cat_counts))
            if unused:
                warnings.append(
                    f"categories in label space with ZERO examples: {unused}. "
                    f"Listing a category without examples teaches the model nothing "
                    f"and can degrade it."
                )
    for w in warnings:
        print(f"WARN  {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if errors:
        print(f"\nFAILED: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    print(f"\nOK: {len(warnings)} warning(s)")
    return 0


# ------------------------------------------------------------------------- from-spans
def from_spans(path: str, output: str | None) -> int:
    """Build OPF JSONL from looser input with `finds` (match-based) and `spans`."""
    out_fh = Path(output).open("w", encoding="utf-8") if output else sys.stdout  # noqa: SIM115
    n = 0
    errors = 0
    try:
        for ln, rec in _read_jsonl(path):
            if isinstance(rec, json.JSONDecodeError):
                print(f"ERROR L{ln}: invalid JSON ({rec})", file=sys.stderr)
                errors += 1
                continue
            text = rec.get("text")
            if not isinstance(text, str):
                print(f"ERROR L{ln}: missing/invalid `text`", file=sys.stderr)
                errors += 1
                continue
            label: list[dict] = [
                {"category": sp["category"], "start": int(sp["start"]), "end": int(sp["end"])}
                for sp in (rec.get("spans", []) or [])
            ]
            for fnd in rec.get("finds", []) or []:
                match, cat = fnd["match"], fnd["category"]
                nth = int(fnd.get("nth", 1))
                idx, found, count = -1, -1, 0
                while True:
                    idx = text.find(match, idx + 1)
                    if idx == -1:
                        break
                    count += 1
                    if count == nth:
                        found = idx
                        break
                if found == -1:
                    print(
                        f"ERROR L{ln}: match {match!r} (nth={nth}) for [{cat}] not found in text",
                        file=sys.stderr,
                    )
                    errors += 1
                    continue
                label.append({"category": cat, "start": found, "end": found + len(match)})
            out = {"text": text, "label": label}
            if "info" in rec:
                out["info"] = rec["info"]
            out_fh.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
    finally:
        if output:
            out_fh.close()
    print(f"wrote {n} record(s)" + (f" -> {output}" if output else ""), file=sys.stderr)
    return 1 if errors else 0


# ---------------------------------------------------------------------------- preview
def preview(path: str, n: int) -> int:
    shown = 0
    for ln, rec in _read_jsonl(path):
        if isinstance(rec, json.JSONDecodeError):
            print(f"L{ln}: invalid JSON", file=sys.stderr)
            continue
        text = rec.get("text", "")
        spans = sorted(_spans_of(rec), key=lambda s: s.get("start", 0))
        out, cur = [], 0
        for sp in spans:
            s, e, c = sp.get("start", 0), sp.get("end", 0), sp.get("category", "?")
            if not (0 <= s < e <= len(text)) or s < cur:
                continue
            out.append(text[cur:s])
            out.append(f"[{c}: {text[s:e]}]")
            cur = e
        out.append(text[cur:])
        print(f"--- L{ln} ---")
        print("".join(out))
        print()
        shown += 1
        if shown >= n:
            break
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="check offsets/overlaps/label-space")
    pv.add_argument("jsonl")
    pv.add_argument("--label-space", help="label_space.json to check category coverage")

    pf = sub.add_parser("from-spans", help="build OPF JSONL (resolves `match` -> offsets)")
    pf.add_argument("jsonl")
    pf.add_argument("--output", help="output path (default: stdout)")

    pp = sub.add_parser("preview", help="render spans inline in the terminal")
    pp.add_argument("jsonl")
    pp.add_argument("--n", type=int, default=10, help="how many records to show")

    args = p.parse_args()
    if args.cmd == "validate":
        return validate(args.jsonl, args.label_space)
    if args.cmd == "from-spans":
        return from_spans(args.jsonl, args.output)
    if args.cmd == "preview":
        return preview(args.jsonl, args.n)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
