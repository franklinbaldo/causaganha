---
type: AgentEvidence
id: "2026-09-14-exciting-mccarthy-to0ars-evidence-green-test"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
kind: "test_green"
reference: "scripts/audit_cnj_parquets.py (VERIFIED_SORTED, VERIFIED_UNSORTED, resolve_verify_values, read_value_order, _audit_file); tests/test_audit_cnj_parquets.py"
summary: "Implemented resolve_verify_values (pure: passes through every non-VERIFY_VALUES classification unchanged, maps order_result True/False/None to VERIFIED_SORTED/VERIFIED_UNSORTED/VERIFY_VALUES) and read_value_order (real DuckDB scan of the actual numero_processo column via read_parquet, SET threads TO 1 to force single-threaded sequential physical-file-order reads, lag() window comparison to detect any adjacent-row inversion; duckdb.Error -> None, an unread gap, never guessed). Wired both into a new _audit_file helper that also de-duplicated the near-identical national-index/per-item audit blocks in audit_catalog. First test run against a naive fixture (values 1..3000 lpad to 3 chars) failed with a real bug in the *test*, not the implementation: values above 999 are 4 digits wide and lpad doesn't truncate, so '1000' < '999' lexicographically -- caught immediately, fixed by widening the fixture to 4-digit padding (CNJ numbers are fixed-width in production so this shape never occurs there, but the test needed matching width to test what it claimed to). `uv run pytest tests/test_audit_cnj_parquets.py -q`: 32/32 pass (26 pre-existing + 6 new). `uv run ruff check .`: all checks passed. `uv run ruff format --check`: one file (the test file) needed reformatting after the new tests were added; ran `uv run ruff format`, re-checked clean."
---

# GREEN: verificação real de valores implementada

`resolve_verify_values` + `read_value_order` implementados e conectados via `_audit_file` (que também eliminou a duplicação entre o bloco do índice nacional e o loop por item em `audit_catalog`). Um teste inicial falhou por um bug no próprio fixture de teste (padding de 3 dígitos insuficiente para valores >999, causando comparação lexicográfica incorreta) -- corrigido para 4 dígitos. 32/32 testes de `test_audit_cnj_parquets.py` passam. `ruff check`/`ruff format --check` limpos.
