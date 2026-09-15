---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal: "Escalar ReviewRecords reais de #1051/RFC 0012 sobre o pool de 48 documentos pendentes (document sem ReviewRecord ainda)"
rationale: "RFC 0012 §5.4 exige >=30 documentos de validação e >=30 de teste adjudicados (~60 ReviewRecords no total) antes do primeiro release do segmentador v8; review_count está em 13 no início desta rodada. O cluster Parquet/CNJ (#1468-1472) segue esgotado no que não depende de credenciais IA ausentes (`env | grep -iE 'IA_|ARCHIVE|CLOUDFLARE|GCP'` sem credenciais reais, confirmado ao vivo). #1051 é a única frente de domínio real, desbloqueada e não esgotada nesta sandbox -- a linhagem de hoje já validou o mecanismo (segunda anotação independente via subagente Técnica 1 isolado + scripts/annotate_second_independent.py + scripts/adjudicate_segmenter_review.py + store.write_review) sobre 13 documentos reais; continuar é o avanço mais direto e desbloqueado disponível, sem competir com nenhum trabalho Wisk em voo (reading-prs confirma nenhuma PR/handoff Wisk ativo)."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 13 para >=15 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um a partir de uma segunda AnnotationRecord genuinamente independente (subagente Técnica 1 isolado, nunca exposto à anotação existente, model_family distinto da anotação original) ingerida por scripts/annotate_second_independent.py, com store.write_review aceitando sem levantar NonIndependentReviewError. Cada resolução de adjudicação cita o disagreement real observado (diff_labels) contra a guideline, não uma preferência mecânica. uv run pytest -q e ruff check/format ficam verdes (exceto a cascata de falhas esperada e documentada pelo próprio scaffold enquanto run.md está em rascunho)."
status: "in_progress"
---

# Goal: escalar ReviewRecords do segmentador (rodada b3xdwp)

Continuação direta do next_move de 2cjjig. Inventário ao vivo confirmou 48
documentos pendentes (38 com 1 anotação, 10 com 2 anotações mas nenhum par
independente). Escolhidos dois candidatos com anotação existente de família
`prompt_subagents:haiku` (distinta de `general-purpose`, a família que os
subagentes desta rodada usarão): doc_dd458d79ebdf7c65daf39d1a51cf1ea9
(acórdão, 3400 chars) e doc_6b714f6515beb1d38ba465e57c60c669 (sentença com
relatório próprio, 4706 chars). Dois subagentes Técnica 1 isolados
(general-purpose, sem visibilidade da anotação existente nem um do outro)
já foram dispatchados em background sobre esses dois documentos.
