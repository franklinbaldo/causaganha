"""Tests for scripts.synthetic_segmenter.specs — DocumentSpec + builders."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.specs import (
    DocumentSpec,
    acordao_moderno_unanime_spec,
    sample_spec,
    sentenca_simples_spec,
)


def test_sentenca_simples_spec_has_no_preliminar_or_dissent() -> None:
    spec = sentenca_simples_spec(seed=1)
    assert spec.doc_type == "sentenca"
    assert spec.has_preliminar is False
    assert spec.has_dissent is False
    assert "preliminar" not in spec.sections
    assert "voto" not in spec.sections


def test_acordao_spec_has_preliminar_and_collegiate_sections() -> None:
    spec = acordao_moderno_unanime_spec(seed=1)
    assert spec.doc_type == "acordao"
    assert spec.has_preliminar is True
    assert "voto" in spec.sections
    assert "acordao_decisorio" in spec.sections


def test_same_seed_reproduces_identical_spec() -> None:
    a = sentenca_simples_spec(seed=42)
    b = sentenca_simples_spec(seed=42)
    assert a == b


def test_different_seed_can_differ() -> None:
    specs = {sentenca_simples_spec(seed=s) for s in range(20)}
    # Not all identical across 20 different seeds (outcome/noise_profile vary).
    assert len({s.outcome for s in specs}) > 1


def test_identity_seed_defaults_to_seed_when_omitted() -> None:
    spec = sentenca_simples_spec(seed=7)
    assert spec.identity_seed == 7


def test_identity_seed_can_be_set_independently() -> None:
    spec = sentenca_simples_spec(seed=7, identity_seed=999)
    assert spec.seed == 7
    assert spec.identity_seed == 999


def test_sample_spec_dispatches_by_family_name() -> None:
    spec = sample_spec("acordao_moderno_unanime", seed=1)
    assert spec.template_family == "acordao_moderno_unanime"


def test_sample_spec_unknown_family_raises() -> None:
    with pytest.raises(ValueError, match="unknown template_family"):
        sample_spec("not_a_real_family", seed=1)


def test_document_spec_rejects_sentenca_with_dissent() -> None:
    with pytest.raises(ValueError, match="voto vencido only exists in acordao"):
        DocumentSpec(
            template_family="sentenca_simples",
            doc_type="sentenca",
            sections=(),
            outcome="procedente",
            has_monetary_award=False,
            has_costs=False,
            has_preliminar=False,
            has_dissent=True,
            noise_profile="clean",
            seed=1,
            identity_seed=1,
        )


def test_document_spec_rejects_unknown_outcome() -> None:
    with pytest.raises(ValueError, match="unknown outcome"):
        DocumentSpec(
            template_family="sentenca_simples",
            doc_type="sentenca",
            sections=(),
            outcome="not_a_real_outcome",
            has_monetary_award=False,
            has_costs=False,
            has_preliminar=False,
            has_dissent=False,
            noise_profile="clean",
            seed=1,
            identity_seed=1,
        )
