---
type: AgentGoal
id: "2026-09-15-exciting-mccarthy-5ov0kv-goal-scale-segmenter-reviews"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal: "Apos mesclar a PR #1527 ja pronta (review_count 23->25), produzir mais um incremento real de ReviewRecords de #1051/RFC 0012 sobre o pool atualizado de documentos com exatamente uma anotacao unseeded (19 candidatos, review_count=25 no inicio deste incremento)."
rationale: "RFC 0012 Sec 5.4 exige >=30 val + >=30 test ReviewRecords adjudicados antes do release v8 do segmentador. Apos o merge de #1527, review_count/evaluation_eligible_count=25 sobre 61 documentos. Cluster Parquet/CNJ (#1468-1472) e o proxy CORS do archive.org (#1482) seguem esgotados no que nao depende de credenciais IA/Cloudflare ausentes deste ambiente. #1051 continua sendo a unica frente de dominio real, desbloqueada e nao esgotada -- 19 documentos remanescentes com exatamente uma anotacao unseeded sao candidatos genuinos a uma segunda anotacao Tecnica 1."
success_signal: "uv run python scripts/segmenter_governance_status.py mostra review_count e evaluation_eligible_count subindo de 25 para >=27 ao final da rodada, com pelo menos 2 novos ReviewRecords reais persistidos em data/segmenter/reviews/, cada um resolvendo uma disagreement real entre a anotacao historica existente e uma segunda anotacao genuinamente independente (subagente isolado, family distinta, prompt_subagents:haiku vs. prompt_subagents:general-purpose existente), ingerida via scripts/annotate_second_independent.py com verbatim-fidelity confirmada programaticamente. store.write_review aceita ambas sem levantar NonIndependentReviewError. uv run pytest tests/segmenter_dataset -q e ruff check/format ficam verdes."
status: "achieved"
---

# Goal: escalar ReviewRecords do segmentador (rodada 5ov0kv, incremento próprio)

Dois documentos-alvo escolhidos entre os 19 candidatos remanescentes com
exatamente uma anotação unseeded e nenhuma review, após o merge de
#1527: `doc_a16e0fd1fc0577af46b35aec522ec446` (4894 chars, sentença;
anotação existente `llm_technique1:batch1`/`prompt_subagents:general-purpose`)
e `doc_b0c364907d4409d67d4d2a734c7bd54d` (6091 chars, acórdão TJRO;
anotação existente `historical_migration:juris_expansion`/
`prompt_subagents:general-purpose`). Dois subagentes Técnica 1 isolados
(`general-purpose`, modelo `haiku` — família `prompt_subagents:haiku`,
distinta da família `prompt_subagents:general-purpose` já em disco para
ambos os documentos) produzem a segunda anotação independente de cada
documento.
