---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-cctnlf-evidence-green-tribunais-merge"
run_id: "2026-09-07-exciting-mccarthy-cctnlf"
goal_id: "2026-09-07-exciting-mccarthy-cctnlf-goal-tribunal-list-merge"
kind: "test_green"
reference: "src/djen_backup/tribunais.py (get_tribunal_list); tests/djen_backup/test_tribunais.py"
summary: "After changing get_tribunal_list to `result = sorted(set(api_codes) | set(TRIBUNAIS))` (was `sorted(set(api_codes))`) and correcting the module/function docstrings to describe the real union behavior, `TRIBUNAL=tjro uv run pytest tests/djen_backup/test_tribunais.py -q` passes 5/5, including the two tests that were RED before (merge test, never-fewer-than-baseline test). Full `TRIBUNAL=tjro uv run pytest -q` run afterwards: only the three known mid-draft artifacts fail (tests/test_check_agent_run_completeness.py's own-tree check, tests/web/test_generate_okf_zod_schemas.py and tests/causaganha_mcp/test_okf_domain_models.py's generated-file drift — see decision-mid-draft-schema-drift.md, independently verified to be caused solely by this round's own in-progress run.md, not by this change), all other tests pass. `uv run ruff check` and `uv run ruff format --check` both clean (one auto-format applied to the new test file, no logic change)."
---

# Evidência GREEN: get_tribunal_list agora faz union

`get_tribunal_list` corrigido para `set(api_codes) | set(TRIBUNAIS)`. 5/5 testes novos passam. Suíte completa fica verde exceto os três artefatos esperados de rascunho (documentados em `decision-mid-draft-schema-drift.md`). `ruff check`/`ruff format --check` limpos.
