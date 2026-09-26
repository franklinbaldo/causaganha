---
type: "RunCheck"
id: "run-checks/20260926t092820z-do-the-best-useful-work-availab/check-verification-final"
run: "runs/20260926T092820Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "Live re-run of scripts/segmenter_governance_status.py, scripts/segmenter_semantic_audit.py, uv run ruff check/format --check, uv run pytest -q tests/segmenter_dataset, and uv run pytest -q (full repository suite, twice -- once before and once after fixing a real test_backlog.py failure this round's own knowledge/backlog/issue-1051.md edit introduced) against the merged/pushed state."
result: "segmenter_governance_status.py: document_count=197, review_count=43, val_count=30 (ceiling), test_count=13 (up from 10), meets_rfc_0012_split_floor=False (need 30). segmenter_semantic_audit.py: 6 findings, exactly matching test_real_store_has_at_most_the_one_known_collapsed_false_positive's existing allowlist (none of this round's 3 documents implicated -- one long_anchor finding this round's own adjudication introduced was caught and fixed before this final check). ruff check/format --check: clean, 462 files. pytest -q tests/segmenter_dataset: 401 passed. pytest -q (full suite): first run caught a real failure (test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round, wrong provenance-id format in this round's own backlog edit); fixed and pushed; second full run: 0 failed, 1 pre-existing skip, exit code 0."
status: "pass"
evidence: "evidence-1051-reviews-ingested"
goal: "run-goals/20260926t092820z-do-the-best-useful-work-availab/goal-1051-test-split-adjudication"
---

# RunCheck
