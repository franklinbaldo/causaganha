---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5crg57-evidence-first-real-review"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
kind: "runtime"
reference: "data/segmenter/reviews/doc_57d1c65ce480854290dc81fd59d4827d/rev_64d8f456961843aa3c90ab0ab822fd1c.xml; docs/planning/evidence/first-real-review-2026-09-15.json"
summary: "Rodando scripts/annotate_second_independent.py contra doc_57d1c65ce480854290dc81fd59d4827d com a reprodução marcada de um subagente (Técnica 1, sem ver a anotação existente) produziu ann_b155b45af373525a533612ecc984cdfe (model_family=prompt_subagents:general-purpose, seeded_with=none) -- independente da anotação pré-existente ann_26e86264539fbbae1cf4c429b1b440f3 (historical_migration_unspecified, seeded_with=none) por mechanical.annotations_are_independent. Rodando scripts/adjudicate_segmenter_review.py com uma resolução escrita por mim (como revisor, comparando as duas anotações e o texto-fonte) produziu rev_64d8f456961843aa3c90ab0ab822fd1c, status=accepted -- store.write_review aceitou sem levantar NonIndependentReviewError, confirmando a independência ao vivo. scripts/segmenter_governance_status.py --store data/segmenter mostra o efeito real: review_count 0->1, evaluation_eligible_count 0->1, blocked_on_reviews True->False."
---

# Evidência: primeiro ReviewRecord real da store

```
$ uv run python scripts/segmenter_governance_status.py --store data/segmenter
{
  "document_count": 61,
  "annotation_count": 75,
  "review_count": 1,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 1,
  "blocked_on_reviews": false
}
```

Antes desta rodada (wvzu11): `review_count=0, evaluation_eligible_count=0, blocked_on_reviews=true`.

As duas anotações divergiram em `fundamentacao_legal` (A tagueou só 1 das 3 citações legais distintas; B tagueou as 3) e nas fronteiras de `custas_inicio`/`custas_fim`. Adjudicação (registrada no próprio `resolution`/`notes` do review) resolveu as duas questões a favor de B, com justificativa citando a guideline (Regra explícita de taguear toda citação distinta em `fundamentacao_legal`; o próprio exemplo da guideline para `custas_inicio` é "Sem custas", igual ao de B).

`uv run python -m segmenter_dataset assign-splits --data-root data/segmenter/ --seed 771` com apenas 1 documento eval-eligible ainda bloqueia (`assign-splits blocked: eval-eligible groups exist but assign_splits produced an empty val (1 docs) or test (0 docs) split`) -- achado honesto registrado: 1 review basta para `evaluation_eligible_count>=1` (o sinal de sucesso deste goal), mas o CLI completo de split precisa de pelo menos 2 documentos eval-eligible (um para val, um para test) para produzir um manifest não-vazio nos dois papéis.
