---
type: "RunCheck"
id: "run-checks/20260914t182457z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260914T182457Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/test_pilot_tjro_2026_real_archive_readback.py tests/test_pilot_tjro_2026_query_cost.py tests/test_validate_pilot_tjro_2026.py tests/test_audit_cnj_parquets.py; uv run pytest -q (full repo suite); uv run ruff check scripts/ tests/; uv run ruff format --check ...; uv run python -m scripts.benchmarks.pilot_tjro_2026_real_archive_readback --output docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json (real network run)"
result: "20/20 new tests green (CORS classification, transient-failure classification, Parquet magic-byte verification, retry-once probe loop against a mocked httpx transport). Full repo suite green (uv run pytest -q, 0 failures, 1 pre-existing unrelated skip). ruff check and ruff format --check both clean. The end-to-end script was independently run for real against archive.org (not mocked), producing docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json with parquet_magic_verified=true and a live-confirmed CORS gap on the download endpoint."
status: "pass"
evidence: "run-evidence/20260914t182457z-do-the-best-useful-work-availab/evidence-real-archive-readback"
goal: "run-goals/20260914t182457z-do-the-best-useful-work-availab/goal-real-archive-readback"
---

# RunCheck
