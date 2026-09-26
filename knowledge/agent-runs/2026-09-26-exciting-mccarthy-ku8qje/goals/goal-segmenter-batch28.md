---
type: AgentGoal
id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal: "Ingerir o Lote 28 de #1050: 2 documentos reais e novos (TJPB/578828501, TJMT/74433596), train-only, seguindo o padrão estabelecido pelos 27 lotes anteriores, para levar `document_count` de 195 para 197 e reabrir o teto real de val/test de RFC 0012 Sec 5 item 4 de 29/29 para >=30/30."
rationale: "`scripts/segmenter_governance_status.py` (executado ao vivo nesta rodada, antes de qualquer trabalho) mostra que o corpus atual de 195 documentos tem um teto de val/test de 29/29 -- um documento abaixo do piso RFC 0012 (>=30/>=30) -- MESMO com 100% de adjudicação do pool existente. A PR #1665 (mesclada por esta rodada) já avançou #1051 (review_count 31->32) mas não pôde tocar esse teto porque adjudicação não cresce o corpus. O próprio handoff que #1665 deixou reconhece isso: '#1050 train-only ingestion batches still need to push document_count from 195 to >=197 so the ceiling itself can reach 30/30 at all -- adjudication alone cannot cross the floor without that.' Escolhido #1050 (crescer o corpus) em vez de continuar #1051 (adjudicar mais) porque #1051 sozinha está temporariamente sem efeito no piso: adjudicar um documento a mais no pool atual não pode elevar um teto que já está no máximo (29/29) até o corpus crescer. TJPB e TJMT foram escolhidos por estarem no tier de menor `store_count` não exaurido (6, empatado com TJMA/TJPA/TJRJ/TJTO/TRF3/TRF5) com candidatos genuinamente disponíveis e livres de quase-duplicata -- TJMA foi descartado por ter apenas 1 candidato remanescente e esse já ter sido rejeitado como quase-duplicata pelo lote 26 (documentado em `knowledge/backlog/issue-1050.md`)."
success_signal: "2 novos `DocumentRecord`/`AnnotationRecord` (train-only) ingeridos em `data/segmenter/` via `scripts/ingest_djen_sample_technique1_batch.py`, verificados por reconstrução verbatim mecânica (`segmenter_dataset.store._text_element_to_labels`) antes do commit; `scripts/segmenter_governance_status.py` mostra `document_count` 195->197 e `val_ceiling_at_full_adjudication`/`test_ceiling_at_full_adjudication` alcançando >=30 (ou demonstra por que não, se a distribuição real dos grupos não cooperar); `scripts/segmenter_semantic_audit.py` sem achados novos; `uv run pytest -q tests/segmenter_dataset` e a suíte completa verdes; `uv run ruff check`/`format --check` limpos; `okf-parser check` conformant; mudanças commitadas, pushed, e PR aberta."
status: "in_progress"
---

# Goal: Lote 28 de #1050 -- crescer o corpus para reabrir o teto de val/test

O corpus atual (195 documentos) tem teto real de val/test em 29/29,
um documento abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30) mesmo com
100% de adjudicação. Adjudicar mais documentos de #1051 não pode mais
mover esse teto -- só crescer o corpus (#1050) pode. Este goal ingere
2 documentos reais e novos (TJPB/578828501, TJMT/74433596), train-only,
seguindo o mesmo padrão dos 27 lotes anteriores.
