---
goal: "Extend the STJ/TJRO WAF-bypass relay (deployment/relay/, src/common/relay.py) to cdn.tse.jus.br/dadosabertos.tse.jus.br, and route src/tse_processual's official ZIP download through it, so issue #985 (blocked on a live Akamai 403 from this sandbox's egress, per knowledge/backlog/issue-985.md) has a code-ready unblock path once the Cloud Function is redeployed."
id: "run-goals/20260910t072709z-do-the-best-useful-work-availab/goal-tse-relay-wiring"
kind: "task-advance"
rationale: "Issue #985 is blocked purely on network egress: TSE's Akamai front 403s every path from this sandbox, exactly the same WAF-block class the relay was built to bypass for STJ/TJRO (Cloud Run southamerica-east1 egress is not blocked, validated live 2026-07-13). The relay's allowlist and src/tse_processual/acquisition.py's download path are the two pieces of code missing to let a future round (or a live-redeployed Cloud Function) exercise the already-merged TSE acquisition/inspection/profiling pipeline without being Akamai-blocked."
run: "runs/20260910T072709Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "New tests/deployment/relay/test_main.py cases proving cdn.tse.jus.br/dadosabertos.tse.jus.br are now allowlisted (RED on unmodified main.py, GREEN after); new tests/tse_processual/test_acquisition.py coverage proving the default download path builds an httpx client wired with common.relay.relay_transport_from_env() and preserves final-URL redirect validation through the relay; full test suite and ruff stay green."
type: "RunGoal"
---

# RunGoal
