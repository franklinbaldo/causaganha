---
goal: "Ingest a 25th real multi-tribunal batch for issue #1050 (segmenter training corpus): 7 documents across TJCE/TJMT/TJRJ/TJTO/TRF3/TRF5 (lowest store_count tier, raising each from 5->6, matching the batch24 pattern) plus TJPI's single remaining pool candidate (store_count 6->7), grown via scripts/ingest_djen_sample_technique1_batch.py."
id: "run-goals/20260920t094145z-do-the-best-useful-work-availab/goal-djen-sample-batch25"
kind: "task-advance"
rationale: "184 documents in the store, val/test ceiling capped at 28/28 (below the RFC 0012 Sec 5 item 4 floor of >=30/>=30) per scripts/segmenter_governance_status.py live-confirmed this round. Growing the corpus (not adjudicating more of the existing pool) is the only way to raise that ceiling, and this exact path (real DJEN sample candidates -> Technique 1 subagent annotation -> verbatim-fidelity ingest) is proven across 24 prior batches with no credential dependency, unlike every other open issue this round (#1471/#1482/#1468-1472 all blocked on absent IA/Cloudflare credentials, reconfirmed this round)."
run: "runs/20260920T094145Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "document_count in data/segmenter/documents advances from 184 to 191 (net, after any near-duplicate rejections), scripts/segmenter_governance_status.py runs clean live on the new state, uv run ruff check/format --check and okf-parser check pass, uv run pytest -q tests/segmenter_dataset passes, and a PR is opened with the new documents plus an updated knowledge/backlog/issue-1050.md narrative."
type: "RunGoal"
---

# RunGoal
