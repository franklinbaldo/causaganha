---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-2cjjig-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
goal: "Escalar ReviewRecords reais de #1051/RFC 0012 sobre o pool de 50 documentos pendentes (document sem ReviewRecord ainda)"
rationale: "RFC 0012 §5.4 exige >=30 documentos de validação e >=30 de teste adjudicados (~60 ReviewRecords no total) antes do primeiro release do segmentador v8; review_count está em 11 no início desta rodada. O cluster Parquet/CNJ (#1468-1472) segue esgotado no que não depende de credenciais IA ausentes (`env | grep -i 'IA_\\|ARCHIVE'` vazio, confirmado ao vivo). #1051 é a única frente de domínio real, desbloqueada e não esgotada nesta sandbox -- a linhagem de hoje já validou o mecanismo (segunda anotação independente via subagente Técnica 1 isolado + scripts/annotate_second_independent.py + scripts/adjudicate_segmenter_review.py + store.write_review) sobre 11 documentos reais; continuar é o avanço mais direto e desbloqueado disponível, sem competir com nenhum trabalho Wisk em voo (reading-prs confirma nenhuma PR/handoff Wisk ativo)."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 11 para >=13 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um a partir de uma segunda AnnotationRecord genuinamente independente (subagente Técnica 1 isolado, nunca exposto à anotação existente, model_family distinto da anotação original) ingerida por scripts/annotate_second_independent.py, com store.write_review aceitando sem levantar NonIndependentReviewError. Cada resolução de adjudicação cita o disagreement real observado (diff_labels) contra a guideline, não uma preferência mecânica. uv run pytest -q e ruff check/format ficam verdes (exceto a cascata de 3 falhas esperada e documentada pelo próprio scaffold enquanto run.md está em rascunho)."
status: "in_progress"
---

# Goal: escalar ReviewRecords do segmentador (rodada 2cjjig)

Continuação direta do next_move de 2jz691. Verifiquei via
`annotations_are_independent` que nenhum dos 10 documentos pendentes que
já têm 2 anotações forma um par independente (todas são repos
seeded/model_draft ou pares de mesma model_family) -- não há atalho de
"só adjudicar", é preciso produzir uma segunda anotação genuinamente
independente para avançar. Escolhidos dois candidatos curtos (acórdão,
~3-3.3k caracteres, anotação existente única de família
`prompt_subagents:haiku`, `seeded_with=none`): doc_613907ccb28de44b6bde
08b443bb369f e doc_69b98539c565dcf153a6bc9a7117b69d. Dois subagentes
Técnica 1 isolados (general-purpose, família distinta da anotação
existente, sem visibilidade dela) já foram dispatchados em background
sobre esses dois documentos. Ao retornarem, cada tagged-file será
ingerido via annotate_second_independent.py e adjudicado via
adjudicate_segmenter_review.py, citando o disagreement real observado.
