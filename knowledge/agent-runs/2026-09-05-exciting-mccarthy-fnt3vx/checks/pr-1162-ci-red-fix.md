---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-fnt3vx-check-pr-1162-ci-red-fix"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
command: "git worktree add /tmp/main-check origin/main --detach && (cd /tmp/main-check && uv run python scripts/generate_okf_domain_models.py) && git -C /tmp/main-check diff --stat -- src/causaganha_mcp/_generated/domain_models.py (no diff, proving the drift is not on main); then on this branch: uv run python scripts/generate_okf_domain_models.py && uv run python scripts/generate_okf_zod_schemas.py && uv run pytest tests/web/test_generate_okf_zod_schemas.py -q && uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-fnt3vx-evidence-ci-red-generated-files-drift"
summary: "Confirmed the generated-file drift did not exist on main (clean worktree regen = no diff), root-caused it to this round's own new AgentCheck without evidence_id, regenerated both affected files, and confirmed tests/web/test_generate_okf_zod_schemas.py (4/4), the full pytest suite (1463 passed/1 skipped), ruff check, and ruff format --check all pass afterward."
---

# Check: causa raiz do CI vermelho da PR #1162 confirmada e corrigida
