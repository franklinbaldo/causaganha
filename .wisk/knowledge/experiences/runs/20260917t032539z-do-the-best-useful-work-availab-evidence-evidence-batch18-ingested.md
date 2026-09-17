---
type: "RunEvidence"
id: "run-evidence/20260917t032539z-do-the-best-useful-work-availab/evidence-batch18-ingested"
run: "runs/20260917T032539Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/ingest_djen_sample_technique1_batch.py run against data/segmenter with docs/planning/evidence/segmenter-djen-sample-batch18-{candidates,overrides}.json and the tagged_final dir; scripts/segmenter_governance_status.py before/after; scripts/segmenter_semantic_audit.py; commit 1986131 on claude/exciting-mccarthy-rm90eg"
summary: "6 documents ingested (TJES/577030718, TJES/577039281, TJRR/568111547, TJRR/568208030, TJMT/74428001, TRF3/42490548). document_count 143->149, annotation_count 196->202, val/test ceiling 21/21->22/22, all confirmed live via scripts/segmenter_governance_status.py. Independent verbatim-fidelity re-verification (strip-tags-and-compare, not just trusting each subagent's self-report) passed byte-for-byte for all 6 before ingestion. 4 documents needed --allowed-unmatched-overrides for dangling pairs verified against raw source text (one being a genuine shared-fim case between custas/honorarios). A 6th tribunal (TRF4) was scanned and fully discarded after discovering its entire remaining pool collapses below the 2500-char floor once the batch3 HTML cleaner strips embedded markup -- new risk class 16, documented in knowledge/backlog/issue-1050.md. uv run ruff check/format --check clean; segmenter_semantic_audit.py found no new findings on the 6 new documents."
goal: "run-goals/20260917t032539z-do-the-best-useful-work-availab/goal-segmenter-batch18"
---

# RunEvidence
