from __future__ import annotations

import random

from segmenter_dataset import dedup
from segmenter_dataset.dedup import (
    content_hash,
    find_exact_duplicates,
    find_near_duplicates,
    near_duplicate_ratio,
    normalize_text,
)


def _brute_force_near_duplicates(
    records: dict[str, str], threshold: float
) -> list[tuple[str, str, float]]:
    """Reference O(n^2) implementation with no pruning -- the pre-optimization contract."""
    ids = list(records)
    out: list[tuple[str, str, float]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            ratio = near_duplicate_ratio(records[ids[i]], records[ids[j]])
            if ratio >= threshold:
                out.append((ids[i], ids[j], ratio))
    return sorted(out, key=lambda t: t[2], reverse=True)


def test_normalize_text_collapses_whitespace_and_lowercases() -> None:
    assert normalize_text("  Foo   Bar\n\tBaz ") == "foo bar baz"


def test_content_hash_ignores_incidental_whitespace() -> None:
    assert content_hash("Foo Bar") == content_hash("foo   bar")


def test_find_exact_duplicates() -> None:
    records = {"a": "Same text", "b": "same   TEXT", "c": "different"}
    pairs = find_exact_duplicates(records)
    assert pairs == [("a", "b")]


def test_find_near_duplicates_threshold() -> None:
    records = {
        "a": "o juiz julgou procedente o pedido do autor",
        "b": "o juiz julgou procedente o pedido da autora",
        "c": "texto completamente diferente sem relacao nenhuma",
    }
    near = find_near_duplicates(records, threshold=0.8)
    ids = {(a, b) for a, b, _ratio in near}
    assert ("a", "b") in ids
    assert ("a", "c") not in ids


def test_find_near_duplicates_matches_brute_force_across_thresholds_and_lengths() -> None:
    """Any length/quick-ratio pruning must never change which pairs are reported.

    Regression guard for the corpus-scale slowdown found live in issue #1050's
    governance script (`scripts/segmenter_governance_status.py` -> `build_groups`
    -> `find_near_duplicates`): 191 real documents took ~500s wall clock because
    every pair got a full `SequenceMatcher.ratio()`, including pairs whose
    length difference alone makes the threshold mathematically unreachable.
    """
    rng = random.Random(42)
    fragments = [
        "o juiz julgou procedente o pedido do autor",
        "condeno o reu ao pagamento de custas processuais",
        "publique-se registre-se intimem-se",
        "texto completamente diferente sem relacao nenhuma com o resto",
        "vistos etc trata-se de acao de cobranca ajuizada",
    ]
    records: dict[str, str] = {}
    for i in range(18):
        repeat = rng.randint(1, 40)
        base = " ".join(rng.choices(fragments, k=repeat))
        # Perturb a handful of copies so some pairs land close to common thresholds.
        if i % 3 == 0 and records:
            base = next(iter(records.values())) + " " + rng.choice(fragments)
        records[f"doc-{i}"] = base

    for threshold in (0.5, 0.7, 0.85, 0.9, 0.95):
        expected = _brute_force_near_duplicates(records, threshold)
        actual = find_near_duplicates(records, threshold=threshold)
        assert actual == expected, f"mismatch at threshold={threshold}"


def test_find_near_duplicates_never_builds_a_matcher_for_length_incompatible_pairs(
    monkeypatch,
) -> None:
    """Pairs whose length ratio makes `threshold` unreachable must skip SequenceMatcher entirely.

    `SequenceMatcher.ratio() == 2*M/T` with `M <= min(len_a, len_b)`, so a pair
    of lengths (short, long) can only reach `threshold` if
    `2*short/(short+long) >= threshold` -- this is a provable upper bound, not
    a heuristic, so pruning on it can never drop a true near-duplicate.
    """
    construction_count = 0
    original_matcher = dedup.SequenceMatcher

    class _CountingMatcher(original_matcher):
        def __init__(self, *args: object, **kwargs: object) -> None:
            nonlocal construction_count
            construction_count += 1
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(dedup, "SequenceMatcher", _CountingMatcher)

    short_texts = {f"short-{i}": "lorem ipsum dolor sit " * 2 for i in range(8)}
    long_texts = {f"long-{i}": "lorem ipsum dolor sit amet consectetur " * 100 for i in range(8)}
    records = {**short_texts, **long_texts}

    dedup.find_near_duplicates(records, threshold=0.9)

    total_pairs = len(records) * (len(records) - 1) // 2
    within_group_pairs = 2 * (8 * 7 // 2)
    assert construction_count <= within_group_pairs
    assert construction_count < total_pairs
