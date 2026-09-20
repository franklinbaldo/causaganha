---
type: "RunCheck"
id: "run-checks/20260919t232524z-do-the-best-useful-work-availab/merge-verification-batch22-batch23"
run: "runs/20260919T232524Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run pytest -q tests/segmenter_dataset -k batch23; uv run pytest -q tests/segmenter_dataset (full); uv run python scripts/segmenter_governance_status.py -- all run against the merge commit (5ad9c7c) on PR #1586's branch before push"
result: "All local checks green: ruff check clean, ruff format --check clean (454 files), okf-parser conformant (0 diagnostics), targeted batch23 regression test pass, full segmenter_dataset suite 100% pass, live governance status confirmed document_count=179/annotation_count=232/val_ceiling=test_ceiling=27 matching the hand-computed merge arithmetic. Pushed; CI then caught one real gap this local pass missed: tests/knowledge/test_backlog.py::test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round failed because knowledge/backlog/issue-1050.md's last_verified_run_id pointed at this round's own Wisk run, whose .wisk/knowledge/experiences/runs/ record only existed on this session's own branch, not in PR #1586's tree -- fixed by copying this round's run records into PR #1586's branch."
status: "pass"
evidence: "merge-verification-batch22-batch23"
---

# RunCheck
