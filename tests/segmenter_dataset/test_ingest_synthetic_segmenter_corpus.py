"""Regression tests for the historical-corpus ingestion script's pairing heuristic.

``_detect_allowed_unmatched`` only gets to auto-excuse a dangling ``_inicio`` as
"runs to the end of the collected text" when it is genuinely positioned last in
the document — no other category's label starts after it. A PR #841 review
found the previous count-only heuristic (``count(_inicio) - count(_fim) == 1``)
excused dangling labels regardless of position, flagging bases that had several
more labeled sections after them as if they ran to the end. These cases are
drawn directly from real documents the review cited as false positives.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from segmenter_dataset.schemas import Label


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "ingest_synthetic_segmenter_corpus",
        Path(__file__).resolve().parents[2] / "scripts" / "ingest_synthetic_segmenter_corpus.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()
_detect_allowed_unmatched = _MODULE._detect_allowed_unmatched


def test_dangling_inicio_with_labeled_sections_after_it_is_not_excused() -> None:
    """doc_020451850468f609103c41689fd50742: capitulo_merito has no _fim, but
    dispositivo_abertura/custas/honorarios/encerramento all start after it —
    a real missing-_fim defect, not a boundary case.
    """
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="relatorio_inicio"),
        Label(start=30, end=40, category="relatorio_fim"),
        Label(start=40, end=50, category="capitulo_merito_inicio"),  # dangling
        Label(start=50, end=60, category="dispositivo_abertura"),
        Label(start=60, end=70, category="custas_inicio"),  # also dangling
        Label(start=70, end=80, category="honorarios_inicio"),
        Label(start=80, end=90, category="honorarios_fim"),
        Label(start=90, end=100, category="encerramento_inicio"),
        Label(start=100, end=110, category="encerramento_fim"),
    ]

    allowed = _detect_allowed_unmatched(labels)

    assert allowed == {}


def test_only_the_positionally_last_dangling_base_is_excused_among_several() -> None:
    """doc_02327ac6189c9f6b3d118b30efd44d2b: custas, honorarios, and encerramento
    all lack a _fim, but only encerramento (the last-starting label in the
    document) is a legitimate "runs to end" case — custas and honorarios each
    have another labeled section starting after them.
    """
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="fundamentacao_legal"),
        Label(start=30, end=40, category="dispositivo_abertura"),
        Label(start=40, end=50, category="resultado"),
        Label(start=50, end=60, category="custas_inicio"),  # dangling, not last
        Label(start=60, end=70, category="honorarios_inicio"),  # dangling, not last
        Label(start=70, end=80, category="encerramento_inicio"),  # dangling, genuinely last
    ]

    allowed = _detect_allowed_unmatched(labels)

    assert allowed == {
        "encerramento": "historical migration: section runs to the end of the collected text"
    }


def test_neither_base_is_excused_when_last_label_is_a_properly_closed_pair() -> None:
    """doc_05626c669226ea47d75a24655624fb07: voto and ementa both lack a _fim,
    but neither is anywhere near the document's actual tail — the last-starting
    label is acordao_decisorio_fim, a properly closed pair. Both dangling bases
    are real defects.
    """
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="relatorio_inicio"),
        Label(start=30, end=40, category="relatorio_fim"),
        Label(start=40, end=50, category="voto_inicio"),  # dangling
        Label(start=50, end=60, category="ementa_inicio"),  # dangling
        Label(start=60, end=70, category="acordao_decisorio_inicio"),
        Label(start=70, end=80, category="resultado"),
        Label(start=80, end=90, category="acordao_decisorio_fim"),  # genuinely last
    ]

    allowed = _detect_allowed_unmatched(labels)

    assert allowed == {}


def test_genuinely_last_dangling_inicio_is_still_excused() -> None:
    """A section whose _inicio really is the last label in the document — nothing
    else starts after it — is the legitimate "runs to the end of the collected
    text" case this heuristic exists for, and must still be excused.
    """
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="relatorio_inicio"),
        Label(start=30, end=40, category="relatorio_fim"),
        Label(start=40, end=50, category="dispositivo_abertura"),
        Label(start=50, end=60, category="resultado"),
        Label(start=60, end=70, category="encerramento_inicio"),  # last label, dangling
    ]

    allowed = _detect_allowed_unmatched(labels)

    assert allowed == {
        "encerramento": "historical migration: section runs to the end of the collected text"
    }


def test_no_dangling_bases_returns_empty_dict() -> None:
    labels = [
        Label(start=0, end=10, category="cabecalho_inicio"),
        Label(start=10, end=20, category="cabecalho_fim"),
        Label(start=20, end=30, category="resultado"),
    ]

    assert _detect_allowed_unmatched(labels) == {}
