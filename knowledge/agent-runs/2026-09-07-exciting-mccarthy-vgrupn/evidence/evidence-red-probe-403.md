---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-vgrupn-evidence-red-probe-403"
run_id: "2026-09-07-exciting-mccarthy-vgrupn"
goal_id: "2026-09-07-exciting-mccarthy-vgrupn-goal-probe-403-rate-limit"
kind: "test_red"
reference: "tests/djen_backup/test_probe.py (new file, 2 tests)"
summary: "Ran `TRIBUNAL=tjro uv run pytest tests/djen_backup/test_probe.py -q` against the unmodified src/djen_backup/probe.py. Both tests fail exactly as predicted by the goal: test_probe_one_skips_403_without_raising fails with `djen_backup.djen.DJENRateLimitedError: CloudFront block (403) — rate limited` raised out of _probe_one (uncaught by either its DJENNotFoundError or (httpx.HTTPError, httpx.RequestError) except clauses); test_probe_worker_keeps_processing_after_a_403 fails the same way, propagating out of _probe_worker. This confirms the defect precisely: a 403 is not swallowed anywhere in probe.py's call chain, unlike engine.py/drain_unknowns.py."
---

# Evidência RED: probe.py propaga DJENRateLimitedError

`tests/djen_backup/test_probe.py` escrito antes de qualquer mudança em `probe.py`. 2/2 testes falham confirmando o defeito: um 403 simulado via `respx` propaga `DJENRateLimitedError` para fora de `_probe_one`/`_probe_worker`, sem nenhum handler capturando.
