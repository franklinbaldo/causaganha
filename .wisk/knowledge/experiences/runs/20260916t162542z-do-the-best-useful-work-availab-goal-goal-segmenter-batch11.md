---
type: "RunGoal"
id: "run-goals/20260916t162542z-do-the-best-useful-work-availab/goal-segmenter-batch11"
run: "runs/20260916T162542Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Ingerir um decimo-primeiro lote real e multi-tribunal de documentos anotados (Tecnica 1) para o corpus de treino do segmenter, avancando a issue #1050 em direcao ao piso de ~200 documentos exigido pela RFC 0012 secao 5 item 4 (corpus_scale_blocks_floor)."
rationale: "Handoff da issue #1471 (Parquet/CNJ, publicacao no IA) segue bloqueado por falta de credenciais (ver check-handoff-environment/check-handoff-disposition). O padrao de lotes reais do segmenter e o unico caminho de avanco real e desbloqueado disponivel nesta rodada: 10 lotes ja mesclados (PRs #1537 a #1559) usando o mesmo mecanismo TDD (RED: teste de regressao exige document_count/eligible_count maior; GREEN: scripts/ingest_djen_sample_technique1_batch.py ingere candidatos reais de data/segmenter_samples/*.jsonl com segunda anotacao independente e adjudicacao)."
success_signal: "scripts/segmenter_governance_status.py mostra document_count estritamente maior que o valor atual (117, pos-merge de PR #1561/#1559) apos o merge do lote 11, com uv run pytest -q tests/segmenter_dataset/ verde incluindo um novo teste de regressao que trava esse crescimento."
status: "active"
---

# RunGoal
