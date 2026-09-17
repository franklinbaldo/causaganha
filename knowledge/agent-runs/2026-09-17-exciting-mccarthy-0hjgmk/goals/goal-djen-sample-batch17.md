---
type: AgentGoal
id: "2026-09-17-exciting-mccarthy-0hjgmk-goal-djen-sample-batch17"
run_id: "2026-09-17-exciting-mccarthy-0hjgmk"
goal: "Ingerir o decimo setimo lote real multi-tribunal para #1050 (RFC 0012)"
rationale: "document_count esta em 138/~200 necessarios para o piso combinado de RFC 0012 Sec 5 item 4 (val/test ceiling precisa chegar a >=30 cada, hoje em 21/21). #1051 (validacao independente) permanece bloqueada estruturalmente ate esse piso ser alcancado. O mecanismo de ingestao (scripts/ingest_djen_sample_technique1_batch.py + subagentes independentes com o prompt canonico Technique 1) ja foi validado por 16 lotes consecutivos; continuar essa linhagem e o avanco real mais direto disponivel para o CausaGanha nesta rodada."
success_signal: "scripts/segmenter_governance_status.py reporta document_count>=143 apos a ingestao, com val_ceiling/test_ceiling>=21 (nao pode regredir); uv run pytest -q tests/segmenter_dataset 100% verde; uv run ruff check/format --check limpos; knowledge/backlog/issue-1050.md atualizado com o registro do lote 17; PR aberta e mesclavel (sem conflito) contra main."
status: "achieved"
---

# Goal: lote 17 do corpus real do segmentador (#1050)

Selecionar candidatos reais e nunca usados de `data/segmenter_samples/*.jsonl`
nos tribunais de menor `store_count` ja representados (TJBA x2, TJMA x2,
TJCE x2), anotar cada um via subagente independente com o prompt canonico
Technique 1 (`data/segmenter_splits/technique1_annotation_prompt.md`),
verificar fidelidade verbatim byte-a-byte (incluindo NBSP genuino onde
presente) e ingerir via
`scripts/ingest_djen_sample_technique1_batch.py`.
