---
type: "RunCheck"
id: "run-checks/20260907t165419z-do-the-best-useful-work-availab/check-full-suite-green"
run: "runs/20260907T165419Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/djen_backup/test_manifest_counts.py -q (before fix, confirm RED); apply fix; uv run pytest tests/djen_backup/ -q; TRIBUNAL=tjro uv run pytest -q; uv run ruff check; uv run ruff format --check"
result: "RED confirmed both new tests failed with the exact predicted stale values (uploaded=0 not 1, has_uploaded_entries=False not True) before the fix. After adding self._invalidate_caches() calls: tests/djen_backup/ 100 passed; full suite pytest -q exit 0, all green; ruff check 'All checks passed!'; ruff format --check '388 files already formatted'."
status: "pass"
evidence: "run-evidence/20260907t165419z-do-the-best-useful-work-availab/evidence-red-green-apply-event"
goal: "run-goals/20260907t165419z-do-the-best-useful-work-availab/goal-fix-apply-event-cache-invalidation"
---

# RunCheck
