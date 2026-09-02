from __future__ import annotations

import pytest
from conftest import make_annotation, make_document, make_review

from segmenter_dataset.dedup import content_hash, near_duplicate_ratio
from segmenter_dataset.splits import (
    EmptyEvalSplitError,
    GroupingKeys,
    SplitAssignment,
    SplitLeakError,
    assign_splits,
    build_groups,
    check_disjoint,
    evaluation_eligible_document_ids,
    train_eligible_document_ids,
    validate_cross_pool_leakage,
    validate_split_leakage,
)


def test_check_disjoint_no_overlap() -> None:
    assert check_disjoint(frozenset({"a"}), frozenset({"b"}), frozenset({"c"})) == []


def test_check_disjoint_reports_overlap() -> None:
    violations = check_disjoint(frozenset({"a", "b"}), frozenset({"b"}), frozenset())
    assert any("train/val overlap" in v for v in violations)


def test_split_assignment_raises_on_overlap() -> None:
    with pytest.raises(SplitLeakError):
        SplitAssignment(frozenset({"a"}), frozenset({"a"}), frozenset())


def test_split_of() -> None:
    assignment = SplitAssignment(frozenset({"a"}), frozenset({"b"}), frozenset({"c"}))
    assert assignment.split_of("a") == "train"
    assert assignment.split_of("b") == "val"
    assert assignment.split_of("c") == "test"
    assert assignment.split_of("z") is None


def test_train_eligible_document_ids_needs_only_annotation() -> None:
    document = make_document()
    annotation = make_annotation(document)
    assert document.document_id in train_eligible_document_ids([annotation])


def test_evaluation_eligible_document_ids_needs_accepted_review() -> None:
    document = make_document()
    a = make_annotation(document, annotator_id="a", model_family="fam-a")
    b = make_annotation(document, annotator_id="b", model_family="fam-b")
    review = make_review(document, [a, b], status="accepted")
    assert document.document_id in evaluation_eligible_document_ids([review])


def test_build_groups_clusters_exact_duplicates() -> None:
    doc_a = make_document(text="texto identico aqui", source_uri="u1")
    doc_b = make_document(text="texto identico aqui", source_uri="u2")
    doc_c = make_document(text="texto completamente diferente", source_uri="u3")
    keys = [GroupingKeys(document_id=d.document_id) for d in (doc_a, doc_b, doc_c)]
    groups = build_groups([doc_a, doc_b, doc_c], keys)
    members_by_group = list(groups.values())
    grouped_pair = {doc_a.document_id, doc_b.document_id}
    assert any(grouped_pair <= members for members in members_by_group)
    assert not any(
        {doc_a.document_id, doc_c.document_id} <= members for members in members_by_group
    )


def test_build_groups_clusters_by_process_number() -> None:
    doc_a = make_document(text="texto A", source_uri="u1")
    doc_b = make_document(text="texto B totalmente distinto", source_uri="u2")
    keys = [
        GroupingKeys(document_id=doc_a.document_id, normalized_process_number="0001234"),
        GroupingKeys(document_id=doc_b.document_id, normalized_process_number="0001234"),
    ]
    groups = build_groups([doc_a, doc_b], keys)
    assert len(groups) == 1


def test_build_groups_from_document_unions_real_duplicate_pair_from_corpus() -> None:
    """Real-corpus regression for PR #838 review finding #1.

    First ~500 chars of two real TJRO sentenças from the
    segmenter-pr2-corpus-ingestion branch (doc_802e3bcb7ef5134b8b98e18f4d71a9d9
    and doc_9c45d216d09c12dbe0b743e0cff5f139), confirmed during corpus audit
    to share the same process number (7000062-51.2022.8.22.0004) in their
    own headers. Exercises the real path end to end:
    ``GroupingKeys.from_document`` -> ``provenance.extract_normalized_process_number``
    -> ``build_groups``, with no mocking of the extraction step. Note this
    particular real pair is template-similar enough (near-dup ratio ~0.96)
    that near-duplicate grouping alone would also catch it; the synthetic
    test below isolates process-number grouping's marginal contribution
    below the near-dup threshold.
    """
    text_a = (
        "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA COMARCA DE OURO PRETO DO OESTE "
        "2ª VARA CÍVEL Av. Daniel Comboni, 1480, 1º Andar. Fórum Des. Cássio "
        "Rodolfo Sbarzi Guedes 76920-000. Ouro Preto do Oeste-RO. Tel.: (69) "
        "3416-1721. E-mail: opo2civel@tjro.jus.br Sala de Atendimento Virtual: "
        "https://meet.google.com/pwx-zsmd-eaf Processo 7000062-51.2022.8.22.0004 "
        "Classe Procedimento Comum Cível Assunto Bem de Família (Voluntário) "
        "Requerente RONALDO CANDIDO RIBEIRO VANUZA SILVA RIBEIRO Advogado(a) "
        "FILIPH MENEZES"
    )
    text_b = (
        "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA COMARCA DE OURO PRETO DO OESTE "
        "2ª VARA CÍVEL Av. Daniel Comboni, 1480, 1º Andar. Fórum Des. Cássio "
        "Rodolfo Sbarzi Guedes 76920-000. Ouro Preto do Oeste-RO. Tel.: (69) "
        "3416-1721. E-mail: opo2civel@tjro.jus.br Sala de Atendimento Virtual: "
        "https://meet.google.com/pwx-zsmd-eaf Processo 7000062-51.2022.8.22.0004 "
        "Classe Procedimento Comum Cível Assunto Bem de Família (Voluntário) "
        "Requerente OUTRA PARTE DIFERENTE Advogado(a) OUTRO ADVOGADO"
    )
    doc_a = make_document(text=text_a, source_uri="real-corpus-802e3bcb")
    doc_b = make_document(text=text_b, source_uri="real-corpus-9c45d216")

    keys = [GroupingKeys.from_document(doc) for doc in (doc_a, doc_b)]
    groups = build_groups([doc_a, doc_b], keys)

    assert len(groups) == 1
    (members,) = groups.values()
    assert members == {doc_a.document_id, doc_b.document_id}


def test_build_groups_from_document_unions_same_processo_below_near_dup_threshold() -> None:
    """Isolates finding #1's marginal contribution over near-dup grouping alone.

    The shared header line is the real, regex-validated format (RFC 0012
    §10's own process-number key); the bodies are deliberately unrelated
    synthetic content (a merits sentença vs. a motion ruling) to keep
    near-dup similarity below the 0.9 default threshold — this is the exact
    leakage scenario the PR #838 review flagged: "two documents that are
    genuinely the same underlying processo but differ more than 0.9 in text
    similarity."
    """
    header = (
        "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA Tribunal de Justiça de Rondônia "
        "Cacoal - 4ª Vara Cível Processo n.: 7007824-46.2021.8.22.0007 Classe: "
        "Procedimento Comum Cível Assunto: Auxílio-Doença Previdenciário "
    )
    body_a = (
        "SENTENÇA Vistos etc. O autor pleiteia a concessão de auxílio doença "
        "junto ao INSS alegando incapacidade laboral decorrente de lesão na "
        "coluna vertebral comprovada por laudo pericial judicial produzido "
        "nos autos após regular instrução processual e contraditório."
    )
    body_b = (
        "DECISÃO Trata-se de embargos de declaração opostos pela parte ré "
        "contra a sentença proferida, alegando omissão quanto ao termo "
        "inicial do benefício concedido. Recebo os embargos e passo à "
        "análise do mérito recursal à luz do art. 1022 do CPC vigente."
    )
    text_a = header + body_a
    text_b = header + body_b
    assert near_duplicate_ratio(text_a, text_b) < 0.9

    doc_a = make_document(text=text_a, source_uri="synthetic-same-processo-a")
    doc_b = make_document(text=text_b, source_uri="synthetic-same-processo-b")

    # Content-hash/near-dup unions must not fire here (that's the point of
    # this test); only the process-number key should.
    content_only_keys = [GroupingKeys(document_id=doc.document_id) for doc in (doc_a, doc_b)]
    content_only_groups = build_groups([doc_a, doc_b], content_only_keys)
    assert len(content_only_groups) == 2

    real_keys = [GroupingKeys.from_document(doc) for doc in (doc_a, doc_b)]
    real_groups = build_groups([doc_a, doc_b], real_keys)
    assert len(real_groups) == 1


def test_assign_splits_respects_eligibility() -> None:
    docs = [
        make_document(text=f"documento numero {i} com texto variado", source_uri=f"u{i}")
        for i in range(10)
    ]
    train_only_ids = frozenset(d.document_id for d in docs[:5])
    eval_ids = frozenset(d.document_id for d in docs[5:])
    groups = {d.document_id: frozenset({d.document_id}) for d in docs}

    assignment = assign_splits(
        groups,
        train_eligible=train_only_ids | eval_ids,
        evaluation_eligible=eval_ids,
        seed=42,
    )

    # Train-only documents must never land in val/test.
    assert train_only_ids.isdisjoint(assignment.val_ids)
    assert train_only_ids.isdisjoint(assignment.test_ids)


def test_assign_splits_raises_when_eval_eligible_groups_starve_val_or_test() -> None:
    """Regression for PR #838 review finding #2.

    Reproduces the exact scenario the review described: every eval-eligible
    group has >= 2 members (as real process-number/near-dup grouping
    produces once finding #1 is wired) and the computed target is 1 — no
    group fits "under target", so the old ``assign_splits`` silently packed
    every one of them into train, leaving val AND test both empty with no
    error raised anywhere (``SplitAssignment``'s disjointness check has
    nothing to catch, since nothing overlaps). This asserts the new code
    raises instead of returning that silently-empty assignment.
    """
    # Deliberately dissimilar bodies within and across families (near-dup
    # ratio well under 0.9) so only the shared document_family key drives
    # grouping — isolates "the group is >= 2 members" from "the group is
    # >= 2 members because of unrelated near-dup contamination".
    bodies = [
        "sentença de mérito julgando procedente o pedido inicial do autor",
        "embargos de declaração opostos pela parte ré quanto ao termo inicial",
        "decisão interlocutória deferindo a tutela de urgência requerida",
        "acórdão que reforma parcialmente a sentença de primeiro grau",
    ]
    docs = [make_document(text=bodies[i], source_uri=f"g{i}") for i in range(4)]
    # Two groups of 2 via a shared grouping key — mirrors what real
    # process-number/near-dup grouping would produce.
    keys = [
        GroupingKeys(document_id=docs[0].document_id, document_family="fam-a"),
        GroupingKeys(document_id=docs[1].document_id, document_family="fam-a"),
        GroupingKeys(document_id=docs[2].document_id, document_family="fam-b"),
        GroupingKeys(document_id=docs[3].document_id, document_family="fam-b"),
    ]
    groups = build_groups(docs, keys)
    assert len(groups) == 2
    assert all(len(members) == 2 for members in groups.values())

    eval_ids = frozenset(doc.document_id for doc in docs)

    with pytest.raises(EmptyEvalSplitError):
        assign_splits(
            groups,
            train_eligible=eval_ids,
            evaluation_eligible=eval_ids,
            train_ratio=0.70,
            val_ratio=0.15,  # total_eligible=4 -> val_target=test_target=1
            seed=1,
        )


def test_assign_splits_allows_empty_eval_when_nothing_is_eval_eligible() -> None:
    """An empty val/test must not raise when there is no eval-eligible data at all.

    E.g. a train-only corpus, early in the annotation pipeline.
    ``EmptyEvalSplitError`` only fires when eval-eligible groups existed but
    got starved out by target sizing.
    """
    docs = [
        make_document(text=f"apenas treino {i} texto variado", source_uri=f"t{i}") for i in range(3)
    ]
    groups = {doc.document_id: frozenset({doc.document_id}) for doc in docs}
    train_ids = frozenset(doc.document_id for doc in docs)

    assignment = assign_splits(
        groups, train_eligible=train_ids, evaluation_eligible=frozenset(), seed=1
    )
    assert assignment.val_ids == frozenset()
    assert assignment.test_ids == frozenset()


def test_assign_splits_is_deterministic() -> None:
    docs = [make_document(text=f"doc {i} texto", source_uri=f"u{i}") for i in range(20)]
    all_ids = frozenset(d.document_id for d in docs)
    groups = {d.document_id: frozenset({d.document_id}) for d in docs}

    first = assign_splits(groups, train_eligible=all_ids, evaluation_eligible=all_ids, seed=7)
    second = assign_splits(groups, train_eligible=all_ids, evaluation_eligible=all_ids, seed=7)
    assert first == second


def test_validate_split_leakage_detects_group_spanning_splits() -> None:
    doc_a = make_document(text="grupo compartilhado", source_uri="u1")
    doc_b = make_document(text="grupo compartilhado", source_uri="u2")
    groups = {doc_a.document_id: frozenset({doc_a.document_id, doc_b.document_id})}
    assignment = SplitAssignment(
        train_ids=frozenset({doc_a.document_id}),
        val_ids=frozenset({doc_b.document_id}),
        test_ids=frozenset(),
    )
    problems = validate_split_leakage(assignment, [doc_a, doc_b], groups)
    assert any("spans multiple splits" in p for p in problems)


def test_validate_cross_pool_leakage_detects_document_id_reuse() -> None:
    """#884: a fresh locked-holdout candidate must not reuse a document_id
    already committed to a previously persisted split — even though that
    split was never loaded into this same ``assign_splits`` call.
    """
    existing = make_document(text="texto do pool ja existente", source_uri="existing-1")
    # Same source_uri -> same content-addressed document_id, different text.
    candidate = make_document(
        text="texto totalmente diferente do candidato", source_uri="existing-1"
    )

    problems = validate_cross_pool_leakage(
        [candidate],
        existing_document_ids=frozenset({existing.document_id}),
        existing_content_hashes=frozenset(),
    )

    assert any("document_id" in p and candidate.document_id in p for p in problems)


def test_validate_cross_pool_leakage_detects_content_hash_reuse() -> None:
    shared_text = "mesmo conteudo compartilhado entre pools distintos"
    candidate = make_document(text=shared_text, source_uri="candidate-2")

    problems = validate_cross_pool_leakage(
        [candidate],
        existing_document_ids=frozenset(),
        existing_content_hashes=frozenset({content_hash(shared_text)}),
    )

    assert any("content_hash" in p for p in problems)


def test_validate_cross_pool_leakage_passes_when_disjoint() -> None:
    candidate = make_document(text="conteudo genuinamente novo e distinto", source_uri="new-3")

    problems = validate_cross_pool_leakage(
        [candidate],
        existing_document_ids=frozenset({"doc_" + "0" * 32}),
        existing_content_hashes=frozenset({"0" * 64}),
    )

    assert problems == []


def test_validate_cross_pool_leakage_detects_near_duplicate() -> None:
    """RFC 0012 §10/§16.1: a near-duplicate cluster must not span pools either —
    not just exact document_id/content_hash reuse (#884).
    """
    existing_text = "Diante do exposto, julgo procedente o pedido inicial formulado pela parte autora"
    # One reworded word: near-dup ratio is high but content_hash differs.
    candidate_text = (
        "Diante do exposto, julgo procedente o pedido inicial formulado pela parte requerente"
    )
    assert near_duplicate_ratio(existing_text, candidate_text) >= 0.9
    assert content_hash(existing_text) != content_hash(candidate_text)

    candidate = make_document(text=candidate_text, source_uri="candidate-4")

    problems = validate_cross_pool_leakage(
        [candidate],
        existing_texts={"existing-4": existing_text},
    )

    assert any(
        "near-duplicate" in p and candidate.document_id in p and "existing-4" in p
        for p in problems
    )


def test_validate_cross_pool_leakage_ignores_dissimilar_existing_text() -> None:
    candidate = make_document(text="conteudo genuinamente novo e distinto", source_uri="new-5")

    problems = validate_cross_pool_leakage(
        [candidate],
        existing_texts={"existing-5": "um texto completamente diferente sem relacao"},
    )

    assert problems == []
