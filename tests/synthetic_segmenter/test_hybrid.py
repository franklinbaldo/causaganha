"""Tests for scripts.synthetic_segmenter.hybrid."""

from __future__ import annotations

import pytest

from scripts.synthetic_segmenter.hybrid import build_hybrid_excerpt, build_hybrid_record
from scripts.synthetic_segmenter.provenance import validate_provenance
from scripts.synthetic_segmenter.specs import sentenca_simples_spec
from scripts.synthetic_segmenter.split_guard import SplitAssignment, SplitLeakError
from scripts.synthetic_segmenter.transform import check_final_invariants


def _assignment() -> SplitAssignment:
    return SplitAssignment(
        train_ids=frozenset({"tjro_sentenca_00"}),
        val_ids=frozenset({"tjro_sentenca_val"}),
        test_ids=frozenset({"tjro_sentenca_test"}),
    )


_RAW_EXCERPT = (
    "A sentença recorrida registrou: Ante o exposto, julgo procedente o pedido. "
    "Processo 7000109-66.2024.8.22.0000. Advogado(a): Eduardo Queiroga (OAB/RO 13431)."
)


def test_build_hybrid_excerpt_scrubs_anchors() -> None:
    excerpt, _occurrences = build_hybrid_excerpt(_RAW_EXCERPT, identity_seed=1)
    assert "o excerto registra que" in excerpt


def test_build_hybrid_excerpt_fictionalizes_identifiers() -> None:
    excerpt, _occurrences = build_hybrid_excerpt(_RAW_EXCERPT, identity_seed=1)
    assert "7000109-66.2024.8.22.0000" not in excerpt
    assert "OAB/RO 13431" not in excerpt


def test_build_hybrid_excerpt_returns_occurrences_found() -> None:
    _excerpt, occurrences = build_hybrid_excerpt(_RAW_EXCERPT, identity_seed=1)
    categories = {occ["category"] for occ in occurrences}
    assert "dispositivo_abertura" in categories
    assert "resultado" in categories


def test_build_hybrid_record_rejects_non_train_source() -> None:
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    with pytest.raises(SplitLeakError):
        build_hybrid_record(
            spec,
            raw_excerpt=_RAW_EXCERPT,
            source_doc_id="tjro_sentenca_val",
            assignment=assignment,
            generator_version="v1",
            corpus_release_id="v1-test-001",
        )


def test_build_hybrid_record_rejects_unknown_source() -> None:
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    with pytest.raises(SplitLeakError):
        build_hybrid_record(
            spec,
            raw_excerpt=_RAW_EXCERPT,
            source_doc_id="never_seen_doc",
            assignment=assignment,
            generator_version="v1",
            corpus_release_id="v1-test-001",
        )


@pytest.mark.parametrize("seed", range(5))
def test_build_hybrid_record_passes_final_invariants(seed: int) -> None:
    spec = sentenca_simples_spec(seed=seed)
    assignment = _assignment()
    record = build_hybrid_record(
        spec,
        raw_excerpt=_RAW_EXCERPT,
        source_doc_id="tjro_sentenca_00",
        assignment=assignment,
        generator_version="v1",
        corpus_release_id="v1-test-001",
    )
    assert check_final_invariants(record["text"], record["label"]) == []


def test_build_hybrid_record_has_valid_hybrid_provenance() -> None:
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    record = build_hybrid_record(
        spec,
        raw_excerpt=_RAW_EXCERPT,
        source_doc_id="tjro_sentenca_00",
        assignment=assignment,
        generator_version="v1",
        corpus_release_id="v1-test-001",
    )
    info = record["info"]
    assert info["source_type"] == "hybrid_synthetic"
    assert info["source_doc_ids"] == ["tjro_sentenca_00"]
    assert info["contains_real_text"] is True
    assert info["generator_version"] == "v1"
    assert info["corpus_release_id"] == "v1-test-001"
    assert validate_provenance(info) == []


def test_build_hybrid_record_promote_hard_negative_records_found_categories() -> None:
    # scrub_mode="promote_hard_negative" leaves the excerpt's anchor
    # phrases untouched -- the record's own provenance must reflect which
    # categories actually turned up in THIS excerpt (dispositivo_abertura,
    # resultado), not just whatever DocumentSpec anticipated ahead of time.
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    record = build_hybrid_record(
        spec,
        raw_excerpt=_RAW_EXCERPT,
        source_doc_id="tjro_sentenca_00",
        assignment=assignment,
        generator_version="v1",
        corpus_release_id="v1-test-001",
        scrub_mode="promote_hard_negative",
    )
    families = set(record["info"].get("hard_negative_families", []))
    assert "dispositivo_abertura" in families
    assert "resultado" in families


def test_build_hybrid_record_neutralize_mode_does_not_fabricate_hard_negatives() -> None:
    # The default "neutralize" mode wraps anchors in reported-speech
    # framing rather than leaving them as hard negatives -- it must not
    # start reporting found categories as hard_negative_families just
    # because build_hybrid_excerpt now surfaces occurrences for every mode.
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    record = build_hybrid_record(
        spec,
        raw_excerpt=_RAW_EXCERPT,
        source_doc_id="tjro_sentenca_00",
        assignment=assignment,
        generator_version="v1",
        corpus_release_id="v1-test-001",
        scrub_mode="neutralize",
    )
    families = set(record["info"].get("hard_negative_families", []))
    assert "dispositivo_abertura" not in families
    assert "resultado" not in families


def test_build_hybrid_record_excerpt_never_reintroduces_a_bare_anchor() -> None:
    """The imported excerpt's own "ante o exposto" mention must not create a
    SECOND dispositivo_abertura label alongside the synthetic operative one
    — the whole point of scrubbing before render.
    """
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    record = build_hybrid_record(
        spec,
        raw_excerpt=_RAW_EXCERPT,
        source_doc_id="tjro_sentenca_00",
        assignment=assignment,
        generator_version="v1",
        corpus_release_id="v1-test-001",
    )
    categories = [lab["category"] for lab in record["label"]]
    assert categories.count("dispositivo_abertura") == 1


def test_build_hybrid_record_merito_body_contains_scrubbed_excerpt() -> None:
    spec = sentenca_simples_spec(seed=1)
    assignment = _assignment()
    record = build_hybrid_record(
        spec,
        raw_excerpt=_RAW_EXCERPT,
        source_doc_id="tjro_sentenca_00",
        assignment=assignment,
        generator_version="v1",
        corpus_release_id="v1-test-001",
    )
    assert "o excerto registra que" in record["text"]
