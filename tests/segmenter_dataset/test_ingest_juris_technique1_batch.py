"""Regression tests for the Technique 1 batch ingestion script's pairing heuristic.

Mirrors ``test_ingest_synthetic_segmenter_corpus.py``: this script has its own
copy of the same ``_detect_allowed_unmatched`` count-only bug (PR #841 review),
fixed the same way — only excuse a dangling ``_inicio`` when it is positioned
last in the document.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from segmenter_dataset.schemas import Label


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "ingest_juris_technique1_batch",
        Path(__file__).resolve().parents[2] / "scripts" / "ingest_juris_technique1_batch.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()
_detect_allowed_unmatched = _MODULE._detect_allowed_unmatched


def test_dangling_inicio_followed_by_more_sections_is_not_excused() -> None:
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="custas_inicio"),  # dangling, not last
        Label(start=30, end=40, category="honorarios_inicio"),
        Label(start=40, end=50, category="honorarios_fim"),
    ]

    assert _detect_allowed_unmatched(labels) == {}


def test_genuinely_last_dangling_inicio_is_still_excused() -> None:
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="resultado"),
        Label(start=30, end=40, category="encerramento_inicio"),  # last label, dangling
    ]

    assert _detect_allowed_unmatched(labels) == {
        "encerramento": "batch1: no closing cue present in source text (region extends to EOD)"
    }


def test_no_dangling_bases_returns_empty_dict() -> None:
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
    ]

    assert _detect_allowed_unmatched(labels) == {}
