"""Behavior tests for scripts/bootstrap_training_corpus.py's load_texts().

load_texts() must derive a stable fallback id for records with no explicit
"id"/"text_uuid" field, so the same text gets the same id across separate
runs of the pipeline (its own two-stage design writes ids to an
intermediate file precisely so they can be cross-referenced later).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import bootstrap_training_corpus as mod


def _expected_stable_id(texto: str) -> str:
    """Same algorithm the fix should use, computed independently of the module."""
    return hashlib.sha256(texto[:200].encode("utf-8")).hexdigest()


def test_load_texts_jsonl_fallback_id_is_deterministic(tmp_path: Path) -> None:
    texto = "Texto de decisão judicial " * 20  # >= 200 chars
    jsonl_path = tmp_path / "texts.jsonl"
    jsonl_path.write_text(json.dumps({"texto": texto}) + "\n", encoding="utf-8")

    rows = mod.load_texts(jsonl_path)

    assert len(rows) == 1
    assert rows[0]["id"] == _expected_stable_id(texto)


def test_load_texts_jsonl_uses_explicit_id_when_present(tmp_path: Path) -> None:
    texto = "Texto de decisão judicial " * 20
    jsonl_path = tmp_path / "texts.jsonl"
    jsonl_path.write_text(
        json.dumps({"texto": texto, "id": "explicit-id"}) + "\n", encoding="utf-8"
    )

    rows = mod.load_texts(jsonl_path)

    assert rows[0]["id"] == "explicit-id"
