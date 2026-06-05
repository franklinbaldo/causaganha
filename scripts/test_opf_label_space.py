#!/usr/bin/env python3
"""T1: Verify OPF label-space O contract empirically.

Builds a 2-example toy dataset and label_space.json, then runs `opf train`
(CPU, 1 epoch, tiny) both ways:
  A) O as first entry in span_class_names -> expected: succeeds
  B) O omitted from span_class_names   -> expected: fails or degrades

Uses v7 ontology with both anchor schemes (single-anchor + start/end pairs).

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

from scripts.prepare_privacy_filter_dataset import (
    LABEL_SPACE_V7,
    SINGLE_ANCHOR_CATEGORIES,
    SPAN_CLASS_NAMES_V7,
)


_TEXT_1 = (
    "EMENTA: Apelacao Civel. Acao de cobranca. "
    "RELATORIO: Trata-se de acao proposta por Joao, "
    "processo n 1234567-89.0123.4.56.7890, conforme art. 927 do CPC. "
    "DO MERITO: Analiso o pedido a luz da Lei n 8.078/90. "
    "Ante o exposto, julgo procedente o pedido e condeno o reu ao "
    "pagamento de R$ 5.000,00 a titulo de danos. "
    "HONORARIOS: Fixo honorarios advocaticios em 10%. "
    "CUSTAS: Custas pelo vencido. "
    "Porto Velho, 15/01/2025. Maria Santos, Juiza."
)

_TEXT_2 = (
    "EMENTA: Recurso de apelacao. Direito civil. "
    "RELATORIO: Cuida-se de recurso interposto contra sentenca. "
    "Posto isso, nego provimento ao recurso, nos termos do art. 932 do CPC. "
    "ENCERRAMENTO: Publique-se. Intimem-se."
)


def _find(text: str, surface: str) -> tuple[int, int]:
    idx = text.find(surface)
    assert idx >= 0, f"{surface!r} not found in text"
    return idx, idx + len(surface)


def _build_toy_records() -> list[dict]:
    s1, e1 = _find(_TEXT_1, "EMENTA:")
    s2, e2 = _find(_TEXT_1, "cobranca.")
    s3, e3 = _find(_TEXT_1, "RELATORIO:")
    s4, e4 = _find(_TEXT_1, "1234567-89.0123.4.56.7890")
    s6, e6 = _find(_TEXT_1, "Ante o exposto")
    s7, e7 = _find(_TEXT_1, "julgo procedente o pedido")
    s8, e8 = _find(_TEXT_1, "R$ 5.000,00")
    s9, e9 = _find(_TEXT_1, "HONORARIOS:")
    s10, e10 = _find(_TEXT_1, "CUSTAS:")

    s11, e11 = _find(_TEXT_2, "EMENTA:")
    s12, e12 = _find(_TEXT_2, "civil.")
    s13, e13 = _find(_TEXT_2, "RELATORIO:")
    s14, e14 = _find(_TEXT_2, "Posto isso")
    s15, e15 = _find(_TEXT_2, "nego provimento")
    s16, e16 = _find(_TEXT_2, "nos termos do art. 932 do CPC")
    s17, e17 = _find(_TEXT_2, "ENCERRAMENTO:")
    s18, e18 = _find(_TEXT_2, "Publique-se. Intimem-se.")

    return [
        {
            "text": _TEXT_1,
            "label": [
                {"category": "ementa_inicio", "start": s1, "end": e1},
                {"category": "ementa_fim", "start": s2, "end": e2},
                {"category": "relatorio_inicio", "start": s3, "end": e3},
                {"category": "ref_processual", "start": s4, "end": e4},
                {"category": "dispositivo_abertura", "start": s6, "end": e6},
                {"category": "resultado", "start": s7, "end": e7},
                {"category": "valor_condenacao", "start": s8, "end": e8},
                {"category": "honorarios_inicio", "start": s9, "end": e9},
                {"category": "custas_inicio", "start": s10, "end": e10},
            ],
        },
        {
            "text": _TEXT_2,
            "label": [
                {"category": "ementa_inicio", "start": s11, "end": e11},
                {"category": "ementa_fim", "start": s12, "end": e12},
                {"category": "relatorio_inicio", "start": s13, "end": e13},
                {"category": "dispositivo_abertura", "start": s14, "end": e14},
                {"category": "resultado", "start": s15, "end": e15},
                {"category": "fundamentacao_legal", "start": s16, "end": e16},
                {"category": "encerramento_inicio", "start": s17, "end": e17},
                {"category": "encerramento_fim", "start": s18, "end": e18},
            ],
        },
    ]


TOY_RECORDS = _build_toy_records()


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
    names = label_space["span_class_names"]
    print(f"\n{'=' * 60}")
    print(f"TEST {label}: span_class_names = {names[:5]}... ({len(names)} total)")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"STDOUT:\n{result.stdout[-500:]}" if result.stdout else "(no stdout)")
    print(f"STDERR:\n{result.stderr[-500:]}" if result.stderr else "(no stderr)")
    print(f"Return code: {result.returncode}")
    return result.returncode


def main() -> int:
    assert len(SPAN_CLASS_NAMES_V7) == 26, f"Expected 26, got {len(SPAN_CLASS_NAMES_V7)}"
    assert SPAN_CLASS_NAMES_V7[0] == "O"

    categories_without_o = SPAN_CLASS_NAMES_V7[1:]
    assert len(categories_without_o) == 25

    single_count = len(SINGLE_ANCHOR_CATEGORIES)
    paired_count = len(categories_without_o) - single_count
    n_cats = len(categories_without_o)
    print(f"v7 ontology: {single_count} single-anchor + {paired_count} paired = {n_cats} + O")

    with tempfile.TemporaryDirectory(prefix="opf_t1_") as tmpdir:
        tmp = Path(tmpdir)

        ls_with_o = LABEL_SPACE_V7.copy()
        rc_a = run_train(ls_with_o, "with_O", tmp)

        ls_without_o = {
            "category_version": "t1_test_without_O",
            "span_class_names": categories_without_o,
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
