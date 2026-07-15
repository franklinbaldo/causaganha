"""Tests for scripts.synthetic_segmenter.diagnostics."""

from __future__ import annotations

from scripts.synthetic_segmenter.diagnostics import (
    anchor_frequency_divergence,
    class_support_by_source_type,
    discriminator_accuracy,
    hard_negative_coverage,
    length_divergence,
    template_family_coverage,
    vocabulary_jsd,
)


def test_discriminator_accuracy_is_high_when_trivially_separable() -> None:
    real = [f"documento real numero {i} sobre processo civil" for i in range(30)]
    synthetic = [f"texto sintetico gerado {i} com marcador exclusivo zzqux" for i in range(30)]
    accuracy = discriminator_accuracy(real, synthetic, seed=1)
    assert accuracy > 0.85


def test_discriminator_accuracy_near_chance_for_identical_distributions() -> None:
    shared_vocab = ["alfa", "beta", "gama", "delta", "epsilon", "zeta"]
    real = [" ".join(shared_vocab[i % 6 : i % 6 + 3]) for i in range(40)]
    synthetic = [" ".join(shared_vocab[(i + 1) % 6 : (i + 1) % 6 + 3]) for i in range(40)]
    accuracy = discriminator_accuracy(real, synthetic, seed=1)
    assert 0.3 <= accuracy <= 0.8


def test_discriminator_accuracy_returns_chance_level_with_too_little_data() -> None:
    assert discriminator_accuracy(["um texto"], [], seed=1) == 0.5
    assert discriminator_accuracy([], [], seed=1) == 0.5


def test_discriminator_accuracy_is_deterministic() -> None:
    real = [f"documento real {i}" for i in range(20)]
    synthetic = [f"texto sintetico {i}" for i in range(20)]
    first = discriminator_accuracy(real, synthetic, seed=7)
    second = discriminator_accuracy(real, synthetic, seed=7)
    assert first == second


def test_length_divergence_reports_means_and_ratio() -> None:
    result = length_divergence([100, 200, 300], [150, 150, 150])
    assert result["real"]["mean"] == 200.0
    assert result["synthetic"]["mean"] == 150.0
    assert result["mean_ratio"] == 0.75


def test_length_divergence_handles_empty_lists() -> None:
    result = length_divergence([], [])
    assert result["real"]["n"] == 0
    assert result["synthetic"]["n"] == 0


def test_vocabulary_jsd_is_zero_for_identical_texts() -> None:
    texts = ["ante o exposto julgo procedente"]
    assert vocabulary_jsd(texts, texts) == 0.0


def test_vocabulary_jsd_is_positive_for_disjoint_vocabularies() -> None:
    real = ["alfa beta gama"]
    synthetic = ["delta epsilon zeta"]
    assert vocabulary_jsd(real, synthetic) > 0.9


def test_vocabulary_jsd_handles_empty_input() -> None:
    assert vocabulary_jsd([], []) == 0.0


def test_anchor_frequency_divergence_reports_per_category_averages() -> None:
    real_labels = [
        [{"category": "resultado", "start": 0, "end": 5}],
        [{"category": "resultado", "start": 0, "end": 5}],
    ]
    synthetic_labels = [
        [{"category": "resultado", "start": 0, "end": 5}],
    ]
    result = anchor_frequency_divergence(real_labels, synthetic_labels)
    assert result["resultado"]["real"] == 1.0
    assert result["resultado"]["synthetic"] == 1.0


def test_anchor_frequency_divergence_includes_categories_only_in_one_side() -> None:
    real_labels = [[{"category": "preliminar_inicio", "start": 0, "end": 5}]]
    synthetic_labels: list[list[dict]] = [[]]
    result = anchor_frequency_divergence(real_labels, synthetic_labels)
    assert result["preliminar_inicio"]["real"] == 1.0
    assert result["preliminar_inicio"]["synthetic"] == 0.0


def test_template_family_coverage_counts_by_family() -> None:
    records = [
        {"info": {"template_family": "sentenca_simples"}},
        {"info": {"template_family": "sentenca_simples"}},
        {"info": {"template_family": "acordao_moderno_unanime"}},
        {"info": {}},
    ]
    coverage = template_family_coverage(records)
    assert coverage == {"sentenca_simples": 2, "acordao_moderno_unanime": 1, "unknown": 1}


def test_hard_negative_coverage_counts_families() -> None:
    records = [
        {"info": {"hard_negative_families": ["quoted_dispositivo"]}},
        {"info": {"hard_negative_families": ["quoted_dispositivo", "reported_prior_outcome"]}},
        {"info": {}},
    ]
    coverage = hard_negative_coverage(records)
    assert coverage == {"quoted_dispositivo": 2, "reported_prior_outcome": 1}


def test_class_support_by_source_type_buckets_by_source_type() -> None:
    records = [
        {
            "info": {"source_type": "pristine_real"},
            "label": [{"category": "resultado", "start": 0, "end": 5}],
        },
        {
            "info": {"source_type": "fully_synthetic"},
            "label": [{"category": "resultado", "start": 0, "end": 5}],
        },
    ]
    support = class_support_by_source_type(records)
    assert support["pristine_real"]["resultado"] == 1
    assert support["fully_synthetic"]["resultado"] == 1


def test_class_support_by_source_type_defaults_to_pristine_real() -> None:
    records = [{"info": {}, "label": [{"category": "resultado", "start": 0, "end": 5}]}]
    support = class_support_by_source_type(records)
    assert support["pristine_real"]["resultado"] == 1
