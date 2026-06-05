#!/usr/bin/env python3
"""T1: Verify OPF label-space O contract empirically.

Builds a 2-example toy dataset and label_space.json, then runs `opf train`
(CPU, 1 epoch, tiny) both ways:
  A) O as first entry in span_class_names → expected: succeeds
  B) O omitted from span_class_names   → expected: fails or degrades

The OPF skill docs are unambiguous: "O must be the first entry in
span_class_names." This script verifies empirically so the decision is
pinned and never re-debated.

Usage (CPU, ~2 min):
    uv pip install "opf @ git+https://github.com/openai/privacy-filter.git"
    python scripts/test_opf_label_space.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


_TEXT_1 = (
    "Ante o exposto, julgo procedente o pedido do autor no processo 1234567-89.0123.4.56.7890."
)
_TEXT_2 = "Posto isso, nego provimento ao recurso, nos termos do art. 932 do CPC."

TOY_RECORDS = [
    {
        "text": _TEXT_1,
        "label": [
            {"category": "dispositivo_abertura", "start": 0, "end": 14},
            {"category": "resultado", "start": 16, "end": 32},
            {"category": "ref_processual", "start": 63, "end": 88},
        ],
    },
    {
        "text": _TEXT_2,
        "label": [
            {"category": "dispositivo_abertura", "start": 0, "end": 10},
            {"category": "resultado", "start": 12, "end": 27},
            {"category": "ref_normativa", "start": 54, "end": 69},
        ],
    },
]


def write_jsonl(records: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_train(label_space: dict, label: str, tmpdir: Path) -> int:
    work = tmpdir / label
    work.mkdir(parents=True, exist_ok=True)

    train_path = work / "train.jsonl"
    val_path = work / "val.jsonl"
    ls_path = work / "label_space.json"
    out_dir = work / "out"

    write_jsonl(TOY_RECORDS, train_path)
    write_jsonl(TOY_RECORDS, val_path)
    ls_path.write_text(json.dumps(label_space, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "opf",
        "train",
        str(train_path),
        "--validation-dataset",
        str(val_path),
        "--label-space-json",
        str(ls_path),
        "--output-dir",
        str(out_dir),
        "--device",
        "cpu",
        "--epochs",
        "1",
        "--batch-size",
        "1",
    ]
    print(f"\n{'=' * 60}")
    print(f"TEST {label}: span_class_names = {label_space['span_class_names']}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"STDOUT:\n{result.stdout[-500:]}" if result.stdout else "(no stdout)")
    print(f"STDERR:\n{result.stderr[-500:]}" if result.stderr else "(no stderr)")
    print(f"Return code: {result.returncode}")
    return result.returncode


def main() -> int:
    categories = [
        "dispositivo_abertura",
        "resultado",
        "ref_processual",
        "valor_condenacao",
        "ref_normativa",
    ]

    with tempfile.TemporaryDirectory(prefix="opf_t1_") as tmpdir:
        tmp = Path(tmpdir)

        # A: O first (should succeed per skill docs)
        ls_with_o = {
            "category_version": "t1_test_with_O",
            "span_class_names": ["O", *categories],
        }
        rc_a = run_train(ls_with_o, "with_O", tmp)

        # B: O omitted (should fail or degrade)
        ls_without_o = {
            "category_version": "t1_test_without_O",
            "span_class_names": categories,
        }
        rc_b = run_train(ls_without_o, "without_O", tmp)

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"  With O first:    rc={rc_a} {'PASS' if rc_a == 0 else 'FAIL'}")
    print(f"  Without O:       rc={rc_b} {'PASS' if rc_b == 0 else 'FAIL'}")

    if rc_a == 0 and rc_b != 0:
        print("\nCONCLUSION: O must be first in span_class_names (confirmed).")
    elif rc_a == 0 and rc_b == 0:
        print("\nCONCLUSION: Both pass. O should still be first per OPF docs.")
    else:
        print("\nCONCLUSION: Unexpected results — investigate manually.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
