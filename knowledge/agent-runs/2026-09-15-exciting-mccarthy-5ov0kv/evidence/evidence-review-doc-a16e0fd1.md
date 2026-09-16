---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5ov0kv-evidence-review-doc-a16e0fd1"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: "2026-09-15-exciting-mccarthy-5ov0kv-goal-scale-segmenter-reviews"
kind: "review"
reference: "data/segmenter/reviews/doc_a16e0fd1fc0577af46b35aec522ec446/rev_ef68f26c75e05e167245e7f7e52a74ed.xml"
summary: "ReviewRecord rev_ef68f26c75e05e167245e7f7e52a74ed para doc_a16e0fd1fc0577af46b35aec522ec446 (sentenca, litigancia de ma-fe/custas), adjudicando a anotacao historica batch1 (ann_d7fff714401c2b8efec8604b9a67a9fa) contra uma segunda anotacao Tecnica 1 genuinamente independente produzida nesta rodada (ann_708369b3cd73122f4e378dc3b5443a5a, subagente general-purpose/haiku isolado)."
---

# Evidência: review doc_a16e0fd1fc0577af46b35aec522ec446

Subagente Técnica 1 isolado (general-purpose, modelo haiku, sem visibilidade
da anotação `batch1` existente) produziu uma reprodução tagueada completa.
`diff_labels` encontrou 7 spans concordantes e 2 discordâncias reais:

1. **cabecalho_fim**: A (novo) = `76801-470` (703-712); B (batch1) = `CEP:
   76801-470` (698-712, inclui o rótulo de campo). Adotado A -- o rótulo
   genérico não é o conteúdo distintivo.
2. **resultado**: A = a oração inteira `CONDENO a parte requerente
   solidariamente com o seu patrono em multa` (68 chars); B = só o verbo
   operativo `CONDENO`. Adotado B -- Rule 1 do guideline ("Anchor spans are
   short — typically 1-5 words") e a tabela ("The operative verb phrase").

**Fidelidade verbatim**: o rascunho inicial do subagente teve 2 defeitos
reais de fidelidade (não apenas discordância de anotação) --
3 espaços do documento-fonte viraram quebras de linha, e 6 aspas curvas
(“ ”) viraram aspas retas ("). Redirecionado duas vezes ao mesmo subagente
(`SendMessage` ao `agentId`) até a reconstrução ficar byte-a-byte idêntica
ao documento armazenado (`_text_element_to_labels` + comparação
programática antes de qualquer ingestão via
`scripts/annotate_second_independent.py`). A última aspa curva restante
foi restaurada por substituição mecânica de um único caractere, numa
posição já confirmada pelo diff programático, sem alterar qualquer span
ou categoria.

`store.write_review` aceitou a resolução sem `NonIndependentReviewError`
(famílias `prompt_subagents:general-purpose` vs. `prompt_subagents:haiku`).
