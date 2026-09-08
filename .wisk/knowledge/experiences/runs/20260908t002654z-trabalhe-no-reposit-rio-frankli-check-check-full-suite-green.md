---
type: "RunCheck"
id: "run-checks/20260908t002654z-trabalhe-no-reposit-rio-frankli/check-full-suite-green"
run: "runs/20260908T002654Z-trabalhe-no-reposit-rio-franklinbaldo-causaganha"
kind: "verification"
procedure: "TRIBUNAL=tjro uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "Full pytest suite green (0 failures), ruff check clean, ruff format --check clean, after landing PR #1296 and the RED->GREEN reset_manifest djen_raw fix."
status: "pass"
---

# RunCheck
