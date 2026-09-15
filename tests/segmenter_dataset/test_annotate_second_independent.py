"""Tests for scripts/annotate_second_independent.py (RFC 0012 §5.3/§8/§9, issue #1050/#1051).

Unlike ``scripts/ingest_juris_technique1_batch.py`` (which mints a brand-new
``DocumentRecord`` per candidate), this script's target document already
exists in the store — it produces the *second*, genuinely independent
annotation a val/test document needs before it can be adjudicated
(``assign_splits``'s evaluation-eligible role, RFC 0012 §10).
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
from conftest import make_document

from segmenter_dataset.ontology import ONTOLOGY_V8


def load_script(module_name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_MODULE = load_script("annotate_second_independent", "scripts/annotate_second_independent.py")

_ONTOLOGY_CATEGORIES = {"cabecalho_inicio", "cabecalho_fim", "resultado", "ref_normativa"}


def test_build_second_annotation_happy_path() -> None:
    document = make_document(text="CABEÇALHO texto julgo procedente fim.")
    tagged = (
        "<cabecalho><inicio>CABEÇALHO</inicio> texto "
        "<resultado>julgo procedente</resultado> <fim>fim.</fim></cabecalho>"
    )

    annotation = _MODULE.build_second_annotation(
        document,
        tagged,
        annotator_id="llm_technique1:second_independent_pilot",
        model_family="prompt_subagents:general-purpose",
        guideline_version="segmenter_v7",
        completed_at="2026-09-15T08:40:00Z",
        ontology_categories=_ONTOLOGY_CATEGORIES,
    )

    assert annotation.annotation_id.startswith("ann_")
    assert annotation.document_id == document.document_id
    assert annotation.annotator_config.model_family == "prompt_subagents:general-purpose"
    assert annotation.annotator_config.seeded_with == "none"
    assert annotation.ontology_version == ONTOLOGY_V8
    assert {label.category for label in annotation.labels} == {
        "cabecalho_inicio",
        "cabecalho_fim",
        "resultado",
    }


def test_ref_normativa_is_dropped_before_validation() -> None:
    document = make_document(text="julgo procedente nos termos do art. 5 fim.")
    tagged = (
        "<resultado>julgo procedente</resultado> nos termos do "
        "<ref_normativa>art. 5</ref_normativa> fim."
    )

    annotation = _MODULE.build_second_annotation(
        document,
        tagged,
        annotator_id="ann1",
        model_family="family-b",
        guideline_version="segmenter_v7",
        completed_at="2026-09-15T08:40:00Z",
        ontology_categories={"resultado"},
    )

    assert [label.category for label in annotation.labels] == ["resultado"]


def test_verbatim_mismatch_raises() -> None:
    document = make_document(text="CABEÇALHO texto fim.")
    tagged = "<cabecalho_inicio>CABEÇALHO</cabecalho_inicio> outro texto fim."

    with pytest.raises(_MODULE.VerbatimFidelityError):
        _MODULE.build_second_annotation(
            document,
            tagged,
            annotator_id="ann1",
            model_family="family-b",
            guideline_version="segmenter_v7",
            completed_at="2026-09-15T08:40:00Z",
            ontology_categories=_ONTOLOGY_CATEGORIES,
        )


def test_mechanical_validation_failure_raises() -> None:
    document = make_document(text="julgo procedente e julgo improcedente.")
    # "resultado" is a single-anchor category that this repo's real ontology
    # never exempts from the at-most-once rule, so tagging it twice without
    # an explicit allow-list must fail mechanical validation.
    tagged = "<resultado>julgo procedente</resultado> e <resultado>julgo improcedente</resultado>."

    with pytest.raises(_MODULE.MechanicalValidationError):
        _MODULE.build_second_annotation(
            document,
            tagged,
            annotator_id="ann1",
            model_family="family-b",
            guideline_version="segmenter_v7",
            completed_at="2026-09-15T08:40:00Z",
            ontology_categories={"resultado"},
        )
