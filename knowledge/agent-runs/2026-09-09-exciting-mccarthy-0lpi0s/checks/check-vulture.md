---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-0lpi0s-check-vulture"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
command: "uvx --python 3.13 vulture src/ scripts/ vulture_whitelist.py --min-confidence 100"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-ci-fix-vulture"
summary: "Reproduced CI's failure (unused 'kwargs' at render_contract_fixture.py:76,80) with the unpinned command first, then confirmed the fix pinned to Python 3.13 (matching CI's 3.12+ runner, since this sandbox's default Python 3.11 can't parse pre-existing PEP 695 generic syntax elsewhere in the repo and produces unrelated noise): exit 0, no findings."
---

# Check: vulture (lint gate)

Reproduzida a falha do CI localmente, corrigida, e reconfirmada limpa (rodando com Python 3.13, batendo com o runner de CI).
