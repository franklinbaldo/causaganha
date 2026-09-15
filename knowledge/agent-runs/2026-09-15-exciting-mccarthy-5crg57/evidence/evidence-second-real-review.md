---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5crg57-evidence-second-real-review"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
kind: "runtime"
reference: "data/segmenter/reviews/doc_e3835a09bb2e497a0407ca9d669a3723/rev_232c7adf1196e0b4ee48ac90df9087df.xml"
summary: "Repeti o mecanismo ponta a ponta num segundo documento (doc_e3835a09bb2e497a0407ca9d669a3723) com um segundo subagente independente, produzindo ann_25d28e06a6fee4293893cb07d078693e e depois rev_232c7adf1196e0b4ee48ac90df9087df (accepted). scripts/segmenter_governance_status.py confirma review_count=2, evaluation_eligible_count=2. Achado honesto: `assign-splits` (CLI completo, não só o diagnóstico) ainda fica bloqueado com 2 documentos eval-eligible -- o algoritmo de assign_splits (RFC 0012 §10, achado de review do PR #838) não tem fallback para grupo menor quando um grupo elegível excede o tamanho-alvo restante, então os 2 documentos caíram ambos no mesmo papel (val) nesta seed, deixando test vazio. Isso não é um bug desta rodada nem do goal (o sinal de sucesso do goal era evaluation_eligible_count>=1, satisfeito desde o primeiro review) -- é uma limitação pré-existente e já documentada do splitter, e fica registrada aqui como achado real para a próxima rodada escalar de propósito (>= 30 val + >= 30 test, RFC 0012 §5.4) em vez de tentar forçar o CLI completo com uma amostra pequena demais para o algoritmo atual."
---

# Evidência: segundo review real, e limite honesto do CLI de splits

```
$ uv run python scripts/segmenter_governance_status.py --store data/segmenter
{
  "document_count": 61,
  "annotation_count": 76,
  "review_count": 2,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 2,
  "blocked_on_reviews": false
}

$ uv run python -m segmenter_dataset assign-splits --data-root data/segmenter/ --seed 771
assign-splits blocked: eval-eligible groups exist but assign_splits produced an empty val (2 docs) or test (0 docs) split — every eligible group likely exceeds the remaining target size, with no fallback to a smaller group (RFC 0012 §10, PR #838 review finding #2); widen val_ratio/test_ratio or grow the pool of independent eval-eligible documents before re-running
```

O disagreement entre as duas anotações deste segundo documento repetiu o padrão do primeiro: `fundamentacao_legal` (A tagueou 1 de 2 citações legais distintas) e, desta vez, `dispositivo_abertura` (A não tagueou nenhuma ocorrência; B tagueou "Considerando a satisfação da obrigação", funcionalmente equivalente aos exemplos da guideline). Adjudicação registrada no próprio `resolution` do review, a favor de B nos dois casos, com justificativa citando a guideline.
