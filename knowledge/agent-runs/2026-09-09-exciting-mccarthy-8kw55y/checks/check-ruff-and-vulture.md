---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-8kw55y-check-ruff-and-vulture"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
command: "uv run ruff check . && uv run ruff format --check . && uvx --python 3.12 vulture src/ scripts/ vulture_whitelist.py --min-confidence 100 (the last one specifically because the 0lpi0s round's PR #1358 lost a CI round-trip to a vulture-only finding ruff/pytest don't catch)"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-diff-fix"
summary: "ruff check: All checks passed! ruff format --check: 403 files already formatted. vulture (pinned to Python 3.12 per 0lpi0s's next_move note, since this sandbox's default 3.11 mis-parses unrelated PEP 695 generics elsewhere in the repo): no findings."
---

# Check: ruff + vulture

Ambos limpos. `vulture` rodado explicitamente porque a rodada anterior perdeu um round-trip de CI por não tê-lo rodado localmente.
