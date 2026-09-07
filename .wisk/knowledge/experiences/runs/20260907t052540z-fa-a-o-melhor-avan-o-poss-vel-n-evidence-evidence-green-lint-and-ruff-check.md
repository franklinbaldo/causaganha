---
type: "RunEvidence"
id: "run-evidence/20260907t052540z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-green-lint-and-ruff-check"
run: "runs/20260907T052540Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "execution"
reference: "local: uv run ruff format src/causaganha_cli/__main__.py; edited two raise ValueError sites; uv run ruff format --check; uv run ruff check"
summary: "After reformatting and assigning raise messages to a local 'msg' variable (matching src/causaganha_mcp/http_server.py's existing pattern) in query() and comunicacoes(), both 'ruff format --check' (384 files already formatted) and 'ruff check' (All checks passed!) are green. ruff check had never actually run in CI for this file, since the lint job's format-check step failed first and stopped the job — TRY003 on the two raw ValueError messages was latent, undetected CI debt this fix also closes."
goal: "goal-fix-pr-1258-lint"
---

# RunEvidence
