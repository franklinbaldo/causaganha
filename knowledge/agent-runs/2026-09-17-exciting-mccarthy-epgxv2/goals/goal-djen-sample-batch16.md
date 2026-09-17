---
type: AgentGoal
id: "2026-09-17-exciting-mccarthy-epgxv2-goal-djen-sample-batch16"
run_id: "2026-09-17-exciting-mccarthy-epgxv2"
goal: "Ingerir decimo sexto lote real multi-tribunal para o corpus de treino do segmentador (#1050)"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test; o corpus real (document_count=132, val_ceiling=test_ceiling=20, ambos verificados ao vivo) ainda esta abaixo desse piso. 15 lotes anteriores ja provaram que scripts/ingest_djen_sample_technique1_batch.py escala sem mudanca de codigo de producao. Um scan ao vivo desta rodada encontrou 220 candidatos reais elegiveis e nunca usados, concentrados nos tribunais de menor store_count (TST=2, TJPI=4, TJGO=9, TJPB=9 no tier store_count=3), confirmando que continuar a cadencia de crescimento de volume e o caminho mais direto para levantar o teto val/test em direcao ao piso RFC."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 132 apos o lote, com annotation_count correspondentemente maior; uv run ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos e o CI passa; o merge e confirmado e registrado; knowledge/backlog/issue-1050.md atualizado com os numeros e qualquer nova classe de risco encontrada."
status: "in_progress"
---

# Goal: decimo sexto lote real multi-tribunal para #1050

Selecionar 6 candidatos reais e nunca usados de `data/segmenter_samples/*.jsonl`
nos tribunais de menor `store_count` ja representados (TST x2, TJPI x2,
TJGO x1, TJPB x1), priorizando volume sobre diversidade de tribunal nova
(seguindo o `next_move` explicito da rodada anterior, j2t668). Os 2
candidatos TST com markup HTML bruto embutido foram limpos com o
limpador ja validado `docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`
antes da anotacao. Anotar cada um via subagente independente com o
prompt canonico Technique 1, ingerir os que passarem na validacao
mecanica/verbatim via `scripts/ingest_djen_sample_technique1_batch.py`,
e atualizar `knowledge/backlog/issue-1050.md` com os numeros e qualquer
achado novo.
