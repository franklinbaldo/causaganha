---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-5lvbii-goal-djen-sample-batch12"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
motivation: "With PR #1562 (batch 11) merged, document_count is live at 119, still far below the >=200 needed to cross RFC 0012 Sec 5 item 4's per-split floor (val/test ceiling stuck at 18/18). knowledge/backlog/issue-1050.md's own next_move says to keep running batches through the proven scripts/ingest_djen_sample_technique1_batch.py mechanism, prioritizing tribunals with low store_count for volume. A live scan of data/segmenter_samples/*.jsonl (excluding TJRO, filtering 2500-18000 chars, Sentenca/Acordao, deduped against the current store) confirms TJES and TJGO are tied for lowest non-single-digit store_count (2 each) with real unused Sentenca candidates carrying a 'preliminar' rare-category cue -- exactly the category #1051's future adjudication needs more coverage of, per the RFC's own rare-category targets."
success_signal: "scripts/ingest_djen_sample_technique1_batch.py ingests TJES/577054686 and TJGO/543562390 as new DocumentRecord+AnnotationRecord pairs (train split, RFC 0012 Sec 8/9); scripts/segmenter_governance_status.py run live afterward reports document_count>=121; a new regression test (RED before ingestion, GREEN after) asserts this; scripts/segmenter_semantic_audit.py reports no new unexplained findings; uv run pytest -q and uv run ruff check/format stay green; a PR is opened and CI passes."
---

# Goal: décimo segundo lote real multi-tribunal (#1050)

TJES e TJGO empatam no menor `store_count` não-singleton (2 cada) com
candidatos Sentença reais e não usados carregando o cue `preliminar`.
Seguindo o próprio `next_move` de `knowledge/backlog/issue-1050.md`:
aumentar volume nos tribunais menos representados, reusando o mecanismo
já provado em 11 lotes anteriores.
