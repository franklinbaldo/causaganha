from __future__ import annotations

from segmenter_dataset.dedup import (
    content_hash,
    find_exact_duplicates,
    find_near_duplicates,
    normalize_text,
)


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
