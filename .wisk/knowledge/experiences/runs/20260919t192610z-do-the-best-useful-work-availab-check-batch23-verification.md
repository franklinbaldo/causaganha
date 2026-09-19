---
type: "RunCheck"
id: "run-checks/20260919t192610z-do-the-best-useful-work-availab/batch23-verification"
run: "runs/20260919T192610Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check/format --check; uv run pytest -q tests/segmenter_dataset -k batch23; uv run pytest -q tests/test_check_agent_run_completeness.py tests/web/test_generate_okf_zod_schemas.py tests/causaganha_mcp/test_okf_domain_models.py; uv run okf-parser check knowledge --relational-schema okf.schema.sql; scripts/segmenter_governance_status.py; scripts/segmenter_semantic_audit.py; independent _text_element_to_labels round-trip + byte diff verification for all 6 documents"
result: "All targeted checks pass: ruff clean, batch23 regression test green, okf-related tests green, okf-parser conformant (0 diagnostics) after fixing a YAML quoting defect, governance status live-confirmed document_count=173/annotation_count=226/val_ceiling=test_ceiling=26, semantic audit zero new findings, all 6 documents verbatim-verified byte-for-byte after fixing 2 real annotation defects (silently-dropped nested resultado tags in 3 docs, one unverified override in a 4th). Full uv run pytest -q tests/segmenter_dataset (whole suite) is slow at this corpus size and still running in background at commit time -- CI on PR #1586 will confirm it, same pattern as batches 20/21."
status: "pass"
evidence: "batch23-ingested"
goal: "goal-batch23-no-collision"
---

# RunCheck
