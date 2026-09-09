---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-8esdwh-check-ruff-and-vulture"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
goal_id: "2026-09-09-exciting-mccarthy-8esdwh-goal-csv-manifest-escaping"
command: "uv run ruff check; uv run ruff format --check; uvx --python 3.12 vulture src/ scripts/ vulture_whitelist.py --min-confidence 100"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-8esdwh-evidence-diff-fix"
summary: "ruff check: all checks passed (repo-wide). ruff format --check: 404 files already formatted. vulture (pinned to Python 3.12 to match CI's lint job, per 0lpi0s's operational note about the default sandbox interpreter): clean, 0 findings."
---

# Check: ruff e vulture

Ambos limpos em todo o repositório, incluindo `vulture` fixado em Python 3.12 conforme a lição operacional registrada por rodadas anteriores.
