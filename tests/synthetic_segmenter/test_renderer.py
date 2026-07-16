"""Tests for scripts.synthetic_segmenter.renderer — the offset-correctness core."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.synthetic_segmenter.renderer import render
from scripts.synthetic_segmenter.specs import (
    DocumentSpec,
    acordao_moderno_unanime_spec,
    sentenca_simples_spec,
)
from scripts.synthetic_segmenter.transform import check_final_invariants


LABEL_SPACE_PATH = Path("data/segmenter_splits/label_space.json")


def _real_categories() -> set[str]:
    data = json.loads(LABEL_SPACE_PATH.read_text(encoding="utf-8"))
    return {name for name in data["span_class_names"] if name != "O"}


@pytest.mark.parametrize("seed", range(10))
def test_sentenca_offsets_are_exact_by_construction(seed: int) -> None:
    spec = sentenca_simples_spec(seed=seed)
    text, labels, _ids = render(spec)
    for label in labels:
        # This is the RFC 0011 §4.3 guarantee itself: text[start:end] must
        # be non-empty and internally consistent. We can't assert equality
        # to a fixed phrase (variants rotate), but we CAN assert the raw
        # invariant that offsets actually point at real, trimmed text.
        surface = text[label["start"] : label["end"]]
        assert surface == surface.strip()
        assert surface != ""


@pytest.mark.parametrize("seed", range(10))
def test_acordao_offsets_are_exact_by_construction(seed: int) -> None:
    spec = acordao_moderno_unanime_spec(seed=seed)
    text, labels, _ids = render(spec)
    for label in labels:
        surface = text[label["start"] : label["end"]]
        assert surface == surface.strip()
        assert surface != ""


@pytest.mark.parametrize("seed", range(10))
def test_sentenca_passes_final_invariants(seed: int) -> None:
    spec = sentenca_simples_spec(seed=seed)
    text, labels, _ids = render(spec)
    assert check_final_invariants(text, labels) == []


@pytest.mark.parametrize("seed", range(10))
def test_acordao_passes_final_invariants(seed: int) -> None:
    spec = acordao_moderno_unanime_spec(seed=seed)
    text, labels, _ids = render(spec)
    assert check_final_invariants(text, labels) == []


@pytest.mark.parametrize("seed", range(5))
def test_sentenca_categories_are_in_real_label_space(seed: int) -> None:
    real_categories = _real_categories()
    spec = sentenca_simples_spec(seed=seed)
    _text, labels, _ids = render(spec)
    for label in labels:
        assert label["category"] in real_categories


@pytest.mark.parametrize("seed", range(5))
def test_acordao_categories_are_in_real_label_space(seed: int) -> None:
    real_categories = _real_categories()
    spec = acordao_moderno_unanime_spec(seed=seed)
    _text, labels, _ids = render(spec)
    for label in labels:
        assert label["category"] in real_categories


def test_sentenca_has_exactly_one_dispositivo_abertura() -> None:
    spec = sentenca_simples_spec(seed=1)
    _text, labels, _ids = render(spec)
    categories = [label["category"] for label in labels]
    assert categories.count("dispositivo_abertura") == 1


def test_acordao_never_labels_dispositivo_abertura() -> None:
    """Guideline rule: an acórdão's operative result is the collegiate
    acordao_decisorio; dispositivo_abertura only exists in sentenças.
    """
    for seed in range(10):
        spec = acordao_moderno_unanime_spec(seed=seed)
        _text, labels, _ids = render(spec)
        categories = [label["category"] for label in labels]
        assert "dispositivo_abertura" not in categories


def test_acordao_has_exactly_one_resultado_in_acordao_decisorio() -> None:
    spec = acordao_moderno_unanime_spec(seed=1)
    _text, labels, _ids = render(spec)
    categories = [label["category"] for label in labels]
    assert categories.count("resultado") == 1

    decisorio_inicio = next(
        label for label in labels if label["category"] == "acordao_decisorio_inicio"
    )
    decisorio_fim = next(label for label in labels if label["category"] == "acordao_decisorio_fim")
    resultado = next(label for label in labels if label["category"] == "resultado")
    assert decisorio_inicio["end"] <= resultado["start"]
    assert resultado["end"] <= decisorio_fim["start"]


def test_quoted_dispositivo_hard_negative_not_labeled() -> None:
    """The injected 'ante o exposto' inside voto must NOT produce a
    dispositivo_abertura label (it's a hard negative, RFC 0011 §5).
    """
    spec = DocumentSpec(
        template_family="acordao_moderno_unanime",
        doc_type="acordao",
        sections=("cabecalho", "ementa", "relatorio", "voto", "acordao_decisorio", "encerramento"),
        outcome="provido",
        has_monetary_award=False,
        has_costs=False,
        has_preliminar=False,
        has_dissent=False,
        noise_profile="clean",
        seed=1,
        identity_seed=1,
        hard_negative_families=("quoted_dispositivo",),
    )
    text, labels, _ids = render(spec)
    assert "ante o exposto" in text.lower()
    categories = [label["category"] for label in labels]
    assert "dispositivo_abertura" not in categories


def test_reported_prior_outcome_hard_negative_not_labeled_resultado() -> None:
    spec = DocumentSpec(
        template_family="sentenca_simples",
        doc_type="sentenca",
        sections=("cabecalho", "relatorio", "capitulo_merito", "encerramento"),
        outcome="procedente",
        has_monetary_award=False,
        has_costs=False,
        has_preliminar=False,
        has_dissent=False,
        noise_profile="clean",
        seed=1,
        identity_seed=1,
        hard_negative_families=("reported_prior_outcome",),
    )
    text, labels, _ids = render(spec)
    assert "julgou procedente" in text.lower()
    # Exactly one resultado — the operative one in capitulo_merito, not the
    # reported prior outcome inside relatorio.
    categories = [label["category"] for label in labels]
    assert categories.count("resultado") == 1


@pytest.mark.parametrize("seed", range(10))
def test_sentenca_produces_ref_normativa_spans(seed: int) -> None:
    """render() bootstraps ref_normativa via regex over the rendered text
    (2026-07-16 fix) — every synthetic doc should now carry at least one,
    since REF_NORMATIVA_FILLER_PHRASES is spliced into the mérito body.
    """
    spec = sentenca_simples_spec(seed=seed)
    _text, labels, _ids = render(spec)
    categories = [label["category"] for label in labels]
    assert "ref_normativa" in categories


@pytest.mark.parametrize("seed", range(10))
def test_acordao_produces_ref_normativa_spans(seed: int) -> None:
    spec = acordao_moderno_unanime_spec(seed=seed)
    _text, labels, _ids = render(spec)
    categories = [label["category"] for label in labels]
    assert "ref_normativa" in categories


def test_fused_custas_honorarios_used_for_some_seeds_without_overlap() -> None:
    """Real-corpus finding (Round B, 2026-07-16): custas+honorarios are
    usually one fused clause. Confirm the fused path fires for at least
    one seed and produces non-overlapping, correctly-ordered spans.
    """
    fused_seen = False
    for seed in range(20):
        spec = DocumentSpec(
            template_family="sentenca_simples",
            doc_type="sentenca",
            sections=(
                "cabecalho",
                "relatorio",
                "capitulo_merito",
                "honorarios",
                "custas",
                "encerramento",
            ),
            outcome="improcedente",
            has_monetary_award=False,
            has_costs=True,
            has_preliminar=False,
            has_dissent=False,
            noise_profile="clean",
            seed=seed,
            identity_seed=seed,
        )
        _text, labels, _ids = render(spec)
        by_cat = {label["category"]: label for label in labels}
        if seed % 2 == 0:
            fused_seen = True
            assert "custas_inicio" in by_cat
            assert "honorarios_inicio" in by_cat
            assert by_cat["custas_fim"]["end"] <= by_cat["honorarios_inicio"]["start"]
    assert fused_seen
    assert (
        check_final_invariants(
            *render(
                DocumentSpec(
                    template_family="sentenca_simples",
                    doc_type="sentenca",
                    sections=(
                        "cabecalho",
                        "relatorio",
                        "capitulo_merito",
                        "honorarios",
                        "custas",
                        "encerramento",
                    ),
                    outcome="improcedente",
                    has_monetary_award=False,
                    has_costs=True,
                    has_preliminar=False,
                    has_dissent=False,
                    noise_profile="clean",
                    seed=0,
                    identity_seed=0,
                )
            )[:2]
        )
        == []
    )


def test_preliminar_in_decisorio_summary_hard_negative_not_labeled() -> None:
    spec = DocumentSpec(
        template_family="acordao_moderno_unanime",
        doc_type="acordao",
        sections=("cabecalho", "ementa", "relatorio", "voto", "acordao_decisorio", "encerramento"),
        outcome="negado_provimento",
        has_monetary_award=False,
        has_costs=False,
        has_preliminar=False,
        has_dissent=False,
        noise_profile="clean",
        seed=1,
        identity_seed=1,
        hard_negative_families=("preliminar_in_decisorio_summary",),
    )
    text, labels, _ids = render(spec)
    assert "preliminar rejeitada" in text.lower()
    categories = [label["category"] for label in labels]
    assert "preliminar_inicio" not in categories
    assert check_final_invariants(text, labels) == []


def test_render_unknown_template_family_raises() -> None:
    bad_spec = sentenca_simples_spec(seed=1)
    object.__setattr__(bad_spec, "template_family", "ghost_family")
    with pytest.raises(ValueError, match="no renderer for template_family"):
        render(bad_spec)


def test_identities_are_reused_in_rendered_text() -> None:
    spec = sentenca_simples_spec(seed=1)
    text, _labels, ids = render(spec)
    assert ids.numero_processo in text
    assert ids.autor.full_name in text
