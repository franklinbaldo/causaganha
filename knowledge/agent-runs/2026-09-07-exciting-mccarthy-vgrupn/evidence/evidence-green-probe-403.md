---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-vgrupn-evidence-green-probe-403"
run_id: "2026-09-07-exciting-mccarthy-vgrupn"
goal_id: "2026-09-07-exciting-mccarthy-vgrupn-goal-probe-403-rate-limit"
kind: "test_green"
reference: "src/djen_backup/probe.py (_probe_one); tests/djen_backup/test_probe.py"
summary: "After adding `except DJENRateLimitedError:` to _probe_one (imports DJENRateLimitedError from djen_backup.djen, logs 'probe_skip_rate_limited' at debug level, marks neither absent nor confirmed so the entry is naturally retried by a future run's fetch_pending_batch query), `TRIBUNAL=tjro uv run pytest tests/djen_backup/test_probe.py -q` passes 2/2, including both tests that were RED before. Full `TRIBUNAL=tjro uv run pytest -q` run afterwards: all tests pass with zero failures (this round's own run.md was not yet in its final state at the time of this specific run — see check-python-suite.md for the full-suite result recorded once the report reached its current state). `uv run ruff check` passed clean on the changed files; `uv run ruff format --check` required one auto-format pass on the new test file (applied), then passed clean."
---

# Evidência GREEN: probe.py agora pula 403 (não marca, não derruba o worker)

`_probe_one` corrigido com `except DJENRateLimitedError:` (loga e ignora, igual a `engine.py`/`drain_unknowns.py`). 2/2 testes novos passam. `ruff check`/`ruff format --check` limpos.
