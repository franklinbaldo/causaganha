---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal: "Escalar ReviewRecords reais de #1051/RFC 0012 sobre o pool de 36 candidatos restantes (documento com exatamente 1 anotação unseeded, sem review)"
rationale: "RFC 0012 §5.4 exige >=30 documentos de validação e >=30 de teste adjudicados antes do primeiro release do segmentador v8; review_count está em 8 no início desta rodada, contra uma meta de ~60 ReviewRecords no total. O cluster Parquet/CNJ (#1468-1471) está esgotado no que não depende de credenciais IA ausentes (#1472 segue bloqueado). #1051 é a única frente de domínio real, desbloqueada e não esgotada nesta sandbox -- a linhagem de 7 rodadas de hoje já validou o mecanismo (segunda anotação independente via subagente Técnica 1 + scripts/annotate_second_independent.py + scripts/adjudicate_segmenter_review.py + store.write_review) sobre 8 documentos reais; continuar é o avanço mais direto e desbloqueado disponível."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 8 para >=10 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um a partir de uma segunda AnnotationRecord genuinamente independente (subagente Técnica 1 isolado, nunca exposto à anotação existente) ingerida por scripts/annotate_second_independent.py, com store.write_review aceitando sem levantar NonIndependentReviewError. Cada resolução de adjudicação cita o disagreement real observado (diff_labels) contra a guideline, não uma preferência mecânica. uv run pytest -q e ruff check/format ficam verdes (exceto a cascata de 3 falhas esperada e documentada pelo próprio scaffold enquanto run.md está em rascunho)."
status: "achieved"
---

# Goal: escalar ReviewRecords do segmentador (rodada 2jz691)

Continuação direta do next_move de 7drjlg: dois subagentes Técnica 1 isolados (sem visibilidade da anotação existente) já foram dispatchados em background sobre dois documentos curtos do pool de 36 candidatos (doc_bef14659dbd6e104f31ccd36359e38b8, doc_f22271af51fd1d9e2e0f296aea1b9617, ambos sentença, família existente historical_migration_unspecified). Ao retornarem, cada tagged-file será ingerido via annotate_second_independent.py e adjudicado via adjudicate_segmenter_review.py, citando o disagreement real observado.
