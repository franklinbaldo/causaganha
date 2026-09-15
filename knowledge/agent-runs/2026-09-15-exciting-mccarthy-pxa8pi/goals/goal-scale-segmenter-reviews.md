---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-pxa8pi-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-pxa8pi"
goal: "Escalar ReviewRecords reais de #1051/RFC 0012 sobre o pool de documentos com exatamente uma anotacao unseeded, continuando o next_move de q4zn8q (review_count=19 no inicio desta rodada)"
rationale: "RFC 0012 Sec 5.4 exige >=30 val + >=30 test ReviewRecords adjudicados antes do release v8 do segmentador; review_count=19/evaluation_eligible_count=19 sobre 61 documentos no inicio da rodada. Cluster Parquet/CNJ (#1468-1472) e o proxy CORS do archive.org (#1482) foram fechados nas ultimas rodadas de hoje (PRs #1519, #1521) e o que resta deles depende de credenciais IA/Cloudflare ausentes deste ambiente (reconfirmado ao vivo). #1051 continua sendo a unica frente de dominio real, desbloqueada e nao esgotada -- inventario ao vivo confirmou 0 documentos genuinamente prontos para adjudicacao imediata (os 10 pares de 2 anotacoes existentes sao todos estruturalmente nao-independentes, seeded_with != 'none' em um dos lados) e 25 documentos com exatamente uma anotacao unseeded, candidatos genuinos a uma segunda anotacao Tecnica 1."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 19 para >=21 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um resolvendo uma disagreement real (nao uma preferencia mecanica) entre uma anotacao historica existente e uma segunda anotacao genuinamente independente (subagente isolado, nunca exposto a anotacao existente, family distinta), ingerida via scripts/annotate_second_independent.py com verbatim-fidelity confirmada programaticamente. store.write_review aceita ambas sem levantar NonIndependentReviewError. uv run pytest tests/segmenter_dataset -q e ruff check/format ficam verdes."
status: "achieved"
---

# Goal: escalar ReviewRecords do segmentador (rodada pxa8pi)

Dois documentos-alvo escolhidos entre os 25 candidatos com exatamente uma
anotacao unseeded e nenhuma review: `doc_9c45d216d09c12dbe0b743e0cff5f139`
(3344 chars, sentenca de correcao de oficio homologando divorcio
consensual) e `doc_8dfe37bb8f3a6d0990cf1a74329f4d1a` (3567 chars, sentenca
homologando acordo em tutela cautelar). Dois subagentes Tecnica 1 isolados
(general-purpose, family `prompt_subagents:general-purpose` -- distinta da
familia `historical_migration_unspecified` da anotacao existente em ambos)
produziram a segunda anotacao independente de cada documento, sem
visibilidade da anotacao existente nem um do outro. O primeiro subagente
(doc_9c45d216) produziu inicialmente um rascunho severamente sub-anotado
(1 unico tag); redirecionado uma vez com o mesmo prompt canonico mais uma
lista explicita de categorias esperadas, produziu uma anotacao completa na
segunda tentativa.

Resultado: review_count 19 -> 21, evaluation_eligible_count 19 -> 21. Ver
evidence-review-doc-8dfe37bb e evidence-review-doc-9c45d216.
