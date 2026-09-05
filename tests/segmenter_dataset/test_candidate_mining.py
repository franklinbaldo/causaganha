from __future__ import annotations

from dataclasses import dataclass

from segmenter_dataset.candidate_mining import (
    RARE_CATEGORIES,
    find_rare_category_hints,
    mine_rare_category_candidates,
)


@dataclass(frozen=True)
class _FakeDocument:
    document_id: str
    text: str


def test_find_rare_category_hints_detects_preliminar() -> None:
    text = "Alega o réu, preliminarmente, a ilegitimidade passiva ad causam."
    assert find_rare_category_hints(text) == {"preliminar"}


def test_find_rare_category_hints_detects_honorarios() -> None:
    text = "Condeno a parte vencida ao pagamento de honorários advocatícios de 10%."
    assert find_rare_category_hints(text) == {"honorarios"}


def test_find_rare_category_hints_detects_custas() -> None:
    text = "Custas processuais pelo vencido, na forma da lei."
    assert find_rare_category_hints(text) == {"custas"}


def test_find_rare_category_hints_detects_voto() -> None:
    text = "VOTO DO RELATOR: acompanho o relator quanto ao mérito do recurso."
    assert find_rare_category_hints(text) == {"voto"}


def test_find_rare_category_hints_detects_acordao_decisorio() -> None:
    text = (
        "ACORDAM os Desembargadores da Turma, à unanimidade de votos, "
        "em negar provimento ao recurso, nos termos do voto do relator."
    )
    # The operative "ACORDAM ... à unanimidade" cue is enough on its own to
    # flag acordao_decisorio, even though this fixture also happens to
    # mention "voto do relator" in prose.
    assert "acordao_decisorio" in find_rare_category_hints(text)


def test_find_rare_category_hints_is_accent_and_case_insensitive() -> None:
    text = "PRELIMINARMENTE, requer o autor a extinção do feito."
    assert find_rare_category_hints(text) == {"preliminar"}


def test_find_rare_category_hints_returns_empty_for_plain_merits_text() -> None:
    text = "No mérito, o contrato foi regularmente celebrado entre as partes."
    assert find_rare_category_hints(text) == frozenset()


def test_find_rare_category_hints_can_match_more_than_one_category() -> None:
    text = (
        "Preliminarmente, rejeito a arguição de nulidade. "
        "Custas processuais pelo vencido. "
        "Honorários advocatícios fixados em 10% sobre a condenação."
    )
    assert find_rare_category_hints(text) == {"preliminar", "custas", "honorarios"}


def test_find_rare_category_hints_respects_category_restriction() -> None:
    text = "Custas processuais pelo vencido. Honorários advocatícios de 10%."
    assert find_rare_category_hints(text, categories=frozenset({"custas"})) == {"custas"}


def test_find_rare_category_hints_never_returns_categories_outside_the_default_set() -> None:
    text = "Preliminarmente, custas, honorários, voto, ACORDAM à unanimidade."
    assert find_rare_category_hints(text) <= RARE_CATEGORIES


def test_mine_rare_category_candidates_buckets_document_ids_by_category() -> None:
    documents = [
        _FakeDocument("doc_a", "Preliminarmente, rejeito a arguição de ilegitimidade."),
        _FakeDocument("doc_b", "Custas processuais pelo vencido."),
        _FakeDocument("doc_c", "No mérito, nada a prover."),
    ]
    result = mine_rare_category_candidates(documents)
    assert result == {
        "preliminar": ("doc_a",),
        "custas": ("doc_b",),
    }


def test_mine_rare_category_candidates_sorts_document_ids_deterministically() -> None:
    documents = [
        _FakeDocument("doc_z", "Custas processuais pelo vencido."),
        _FakeDocument("doc_a", "Custas judiciais na forma da lei."),
    ]
    result = mine_rare_category_candidates(documents)
    assert result["custas"] == ("doc_a", "doc_z")


def test_mine_rare_category_candidates_lists_a_document_under_every_hit_category() -> None:
    documents = [
        _FakeDocument(
            "doc_multi",
            "Preliminarmente, arguida a nulidade. Custas processuais pelo vencido.",
        ),
    ]
    result = mine_rare_category_candidates(documents)
    assert result["preliminar"] == ("doc_multi",)
    assert result["custas"] == ("doc_multi",)


def test_mine_rare_category_candidates_empty_input_returns_empty_mapping() -> None:
    assert mine_rare_category_candidates([]) == {}
