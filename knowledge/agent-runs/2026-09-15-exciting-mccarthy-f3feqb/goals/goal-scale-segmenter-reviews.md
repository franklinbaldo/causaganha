---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-f3feqb-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
goal: "Escalar ReviewRecords reais de #1051/RFC 0012 sobre o pool de documentos pendentes (document sem ReviewRecord ainda)"
rationale: "RFC 0012 §5.4 exige >=30 documentos de validação e >=30 de teste adjudicados (~60 ReviewRecords no total) antes do primeiro release do segmentador v8; review_count está em 15 no início desta rodada. O cluster Parquet/CNJ (#1468-1472) segue esgotado no que não depende de credenciais IA ausentes (env vazio, confirmado ao vivo). #1051 é a única frente de domínio real, desbloqueada e não esgotada nesta sandbox -- a linhagem de hoje já validou o mecanismo (segunda anotação independente via subagente Técnica 1 isolado + scripts/annotate_second_independent.py + scripts/adjudicate_segmenter_review.py + store.write_review) sobre 15 documentos reais; continuar é o avanço mais direto e desbloqueado disponível, sem competir com nenhum trabalho Wisk em voo (reading-prs confirma nenhuma PR/handoff Wisk ativo)."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 15 para >=17 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um a partir de uma segunda AnnotationRecord genuinamente independente (subagente Técnica 1 isolado, nunca exposto à anotação existente, model_family distinto da anotação original) ingerida por scripts/annotate_second_independent.py, com store.write_review aceitando sem levantar NonIndependentReviewError. Cada resolução de adjudicação cita o disagreement real observado (diff_labels) contra a guideline, não uma preferência mecânica. uv run pytest -q e ruff check/format ficam verdes (exceto a cascata de falhas esperada e documentada pelo próprio scaffold enquanto run.md está em rascunho)."
status: "active"
---

# Goal: escalar ReviewRecords do segmentador (rodada f3feqb)

Continuação direta do next_move de yz281l (que fechou o item 1 do
checklist de #1468 e apontou #1051 como frente de maior momentum real).
Inventário ao vivo confirmou 46 documentos ainda sem review: 10 com 2
anotações mas nenhum par independente (confirmado via
`annotations_are_independent`, todos False -- mesmo padrão de rodadas
anteriores), 36 com exatamente 1 anotação. Escolhidos dois candidatos
curtos com anotação existente de família `prompt_subagents:general-purpose`
(independent-capable, `seeded_with="none"`): doc_7e5b8558463338f1f74ee7ba8924ccfa
(sentença de Juizado Especial, 2062 chars) e
doc_ad9d4a846d91353b317e3017245ffee5 (sentença de execução contra a
Fazenda Pública, 2112 chars). Dois subagentes Técnica 1 isolados (modelo
haiku, família `prompt_subagents:haiku` -- distinta da anotação existente
de ambos os documentos) foram dispatchados em background sobre esses dois
documentos, sem visibilidade da anotação existente nem um do outro.
