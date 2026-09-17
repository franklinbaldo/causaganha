---
type: "RunGoal"
id: "run-goals/20260917t082642z-do-the-best-useful-work-availab/batch21-trf2"
run: "runs/20260917T082642Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Ingest a 21st real multi-tribunal Technique 1 annotation batch for issue #1050 (segmenter corpus), sampling TRF2 (store_count=4, next live-eligible tier per knowledge/backlog/issue-1050.md's batch20 writeup)"
rationale: "Continues a proven 20-batch lineage (document_count 61->161) with a live-confirmed unblocked next step: a fresh live scan of data/segmenter_samples/trf2.jsonl + trf2_acordao.jsonl (correct field names text/info.id/info.tribunal/info.tipoDocumento) excluding the 9 TRF2 ids already ingested found 13 eligible Acordao/Sentenca candidates >=2500 chars after HTML cleaning; picked the top 6 by length, all Acordao."
success_signal: "scripts/segmenter_governance_status.py document_count increases from 161 to 167 (6 new documents), uv run pytest -q tests/segmenter_dataset stays green, ruff check/format clean, and each new document's tagged reconstruction matches its source text byte-for-byte."
status: "active"
---

# RunGoal
