---
goal: "Ingest an 18th real multi-tribunal batch into the segmenter training corpus (issue #1050, RFC 0012 Sec 5 item 4) via scripts/ingest_djen_sample_technique1_batch.py: 6 documents (TJES x2, TJRR x2, TJMT x1, TRF3 x1 -- all Sentenca), selected by live-scanning data/segmenter_samples/*.jsonl for never-used, >=2500-char (post-cleaning) candidates in the lowest store_count tribunals (TJMG/TJRN/TJSE/TJRS confirmed pool-exhausted this round; TRF4's entire remaining pool also confirmed unusable -- every candidate collapses below the 2500-char floor after HTML-markup stripping, a new finding)."
id: "run-goals/20260917t032539z-do-the-best-useful-work-availab/goal-segmenter-batch18"
kind: "task-advance"
rationale: "Continues the established, unblocked, credential-free lineage (17 prior batches, document_count 61->143 live-confirmed) while issue #1471's IA-publish handoff stays blocked on missing credentials; per knowledge/backlog/issue-1050.md this is the only real path toward RFC 0012's >=30/>=30 val/test floor."
run: "runs/20260917T032539Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "scripts/segmenter_governance_status.py reports document_count increased from 143 to 149 (or the live count at merge time, if a concurrent session also lands a batch first) with val_ceiling/test_ceiling >= 21/21, confirmed live after merge; uv run pytest -q tests/segmenter_dataset/ green against the new HEAD; PR merged."
type: "RunGoal"
---

# RunGoal
