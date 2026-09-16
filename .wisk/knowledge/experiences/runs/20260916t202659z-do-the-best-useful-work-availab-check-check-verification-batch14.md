---
type: "RunCheck"
id: "run-checks/20260916t202659z-do-the-best-useful-work-availab/check-verification-batch14"
run: "runs/20260916T202659Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/segmenter_dataset/; uv run ruff check tests/segmenter_dataset/test_segmenter_governance_status.py; uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs; uv run python scripts/segmenter_semantic_audit.py --store data/segmenter; live document_count check via SegmenterDatasetStore.list_documents()"
result: "pytest tests/segmenter_dataset/: all green (ran twice, once in the /tmp/pr1567 merge worktree and once on this session's own branch after re-applying the diff as a patch); ruff check clean; okf-parser check knowledge conformant, 0 diagnostics; check_agent_run_completeness.py all reports complete; segmenter_semantic_audit.py shows only pre-existing findings unrelated to the 3 new documents (doc_002ffad9/doc_a1e8833b/doc_d0ba3e47 do not appear); live document_count==126 with exactly the 3 new hashes (d6ee41ce/dfbd4832/fe3392b2) present and the duplicate TJSE hash (1d59d889) confirmed absent."
status: "pass"
evidence: "evidence-batch14-dedup-fix"
---

# RunCheck
