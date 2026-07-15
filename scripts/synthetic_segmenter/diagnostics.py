"""Cheap, deterministic diagnostics before any LLM judge (RFC 0011 §9, §14).

"O juiz LLM não é requisito para o treino sintético inicial." This module
is the gate Phase 3's ``llm_judge.py`` depends on existing first — every
function here is stdlib/numpy only, no model calls, no network:

- ``discriminator_accuracy`` — a minimal Naive Bayes bag-of-words
  classifier's holdout accuracy at telling real from synthetic text.
  **Interpretation, not a verdict**: an easy discriminator is diagnostic
  evidence, not proof the synthetic data is useless — synthetic examples
  can differ deliberately from real ones and still teach useful
  invariances. Read this alongside real-validation performance, never
  alone (RFC 0011 §9).
- ``length_divergence`` — summary-stat comparison of document lengths.
- ``vocabulary_jsd`` — Jensen-Shannon divergence between word-frequency
  distributions.
- ``anchor_frequency_divergence`` — per-category label-count-per-document
  comparison.
- ``template_family_coverage`` / ``hard_negative_coverage`` /
  ``class_support_by_source_type`` — the coverage/support counts §9 lists
  alongside the statistical checks.

Near-duplicate/exact-duplicate detection already lives in ``dedup.py``
(Foundation layer) — this module doesn't reimplement it.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def discriminator_accuracy(
    real_texts: list[str],
    synthetic_texts: list[str],
    *,
    seed: int = 0,
    holdout_fraction: float = 0.3,
) -> float:
    """Holdout accuracy of a multinomial Naive Bayes real-vs-synthetic classifier.

    Deterministic in ``seed``. Returns ``0.5`` (chance level) if either
    class has fewer than 2 examples after the holdout split — too little
    data to train or evaluate meaningfully.
    """
    rng = np.random.default_rng(seed)

    def _split(texts: list[str]) -> tuple[list[str], list[str]]:
        indices = rng.permutation(len(texts))
        n_holdout = max(1, round(len(texts) * holdout_fraction)) if texts else 0
        holdout_idx = set(indices[:n_holdout].tolist())
        train = [t for i, t in enumerate(texts) if i not in holdout_idx]
        holdout = [t for i, t in enumerate(texts) if i in holdout_idx]
        return train, holdout

    real_train, real_holdout = _split(real_texts)
    synth_train, synth_holdout = _split(synthetic_texts)

    if len(real_train) < 1 or len(synth_train) < 1 or not (real_holdout or synth_holdout):
        return 0.5

    vocab: dict[str, int] = {}
    for text in real_train + synth_train:
        for token in _tokenize(text):
            vocab.setdefault(token, len(vocab))
    if not vocab:
        return 0.5

    def _counts(texts: list[str]) -> np.ndarray:
        counts = np.zeros(len(vocab), dtype=np.float64)
        for text in texts:
            for token in _tokenize(text):
                idx = vocab.get(token)
                if idx is not None:
                    counts[idx] += 1
        return counts

    real_counts = _counts(real_train) + 1.0  # Laplace smoothing
    synth_counts = _counts(synth_train) + 1.0
    real_log_probs = np.log(real_counts / real_counts.sum())
    synth_log_probs = np.log(synth_counts / synth_counts.sum())

    prior_real = len(real_train) / (len(real_train) + len(synth_train))
    log_prior_real = math.log(prior_real)
    log_prior_synth = math.log(1 - prior_real)

    def _predict_is_real(text: str) -> bool:
        score_real = log_prior_real
        score_synth = log_prior_synth
        for token in _tokenize(text):
            idx = vocab.get(token)
            if idx is not None:
                score_real += real_log_probs[idx]
                score_synth += synth_log_probs[idx]
        return score_real >= score_synth

    correct = sum(1 for t in real_holdout if _predict_is_real(t))
    correct += sum(1 for t in synth_holdout if not _predict_is_real(t))
    total = len(real_holdout) + len(synth_holdout)
    return correct / total if total else 0.5


def length_divergence(real_lengths: list[int], synthetic_lengths: list[int]) -> dict:
    """Summary-stat comparison of document character lengths."""

    def _stats(values: list[int]) -> dict:
        if not values:
            return {"mean": 0.0, "std": 0.0, "n": 0}
        arr = np.array(values, dtype=np.float64)
        return {"mean": float(arr.mean()), "std": float(arr.std()), "n": len(values)}

    real_stats = _stats(real_lengths)
    synth_stats = _stats(synthetic_lengths)
    mean_ratio = synth_stats["mean"] / real_stats["mean"] if real_stats["mean"] else float("nan")
    return {"real": real_stats, "synthetic": synth_stats, "mean_ratio": mean_ratio}


def _word_freq(texts: list[str]) -> Counter:
    counter: Counter = Counter()
    for text in texts:
        counter.update(_tokenize(text))
    return counter


def vocabulary_jsd(real_texts: list[str], synthetic_texts: list[str]) -> float:
    """Jensen-Shannon divergence (base 2, in [0, 1]) between word-frequency distributions.

    0.0 = identical vocabulary distributions; 1.0 = maximally divergent
    (disjoint supports). Returns 0.0 if either side has no tokens.
    """
    real_counts = _word_freq(real_texts)
    synth_counts = _word_freq(synthetic_texts)
    vocab = sorted(set(real_counts) | set(synth_counts))
    if not vocab:
        return 0.0

    real_total = sum(real_counts.values()) or 1
    synth_total = sum(synth_counts.values()) or 1
    p = np.array([real_counts.get(w, 0) / real_total for w in vocab])
    q = np.array([synth_counts.get(w, 0) / synth_total for w in vocab])
    m = 0.5 * (p + q)

    def _kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def anchor_frequency_divergence(
    real_labels: list[list[dict]], synthetic_labels: list[list[dict]]
) -> dict:
    """Per-category average label count per document, real vs. synthetic.

    ``real_labels``/``synthetic_labels`` are lists of one document's label
    list each (i.e. ``[doc1_labels, doc2_labels, ...]``).
    """

    def _avg_counts(all_labels: list[list[dict]]) -> dict[str, float]:
        n_docs = len(all_labels) or 1
        totals: Counter = Counter()
        for labels in all_labels:
            for label in labels:
                totals[label["category"]] += 1
        return {cat: count / n_docs for cat, count in totals.items()}

    real_avg = _avg_counts(real_labels)
    synth_avg = _avg_counts(synthetic_labels)
    categories = sorted(set(real_avg) | set(synth_avg))
    return {
        cat: {"real": real_avg.get(cat, 0.0), "synthetic": synth_avg.get(cat, 0.0)}
        for cat in categories
    }


def template_family_coverage(records: list[dict]) -> dict[str, int]:
    """Count of records per ``info.template_family`` (missing -> ``"unknown"``)."""
    counter: Counter = Counter()
    for record in records:
        counter[record.get("info", {}).get("template_family", "unknown")] += 1
    return dict(counter)


def hard_negative_coverage(records: list[dict]) -> dict[str, int]:
    """Count of records containing each hard-negative family."""
    counter: Counter = Counter()
    for record in records:
        for family in record.get("info", {}).get("hard_negative_families") or []:
            counter[family] += 1
    return dict(counter)


def class_support_by_source_type(records: list[dict]) -> dict[str, dict[str, int]]:
    """Nested ``{source_type: {category: label_count}}`` support table."""
    result: dict[str, Counter] = {}
    for record in records:
        source_type = record.get("info", {}).get("source_type", "pristine_real")
        bucket = result.setdefault(source_type, Counter())
        for label in record.get("label", []):
            bucket[label["category"]] += 1
    return {source_type: dict(counts) for source_type, counts in result.items()}
