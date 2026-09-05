---
type: AgentDecision
id: "2026-09-05-eager-wozniak-5akx2o-decision-project-owned-checker"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
question: "Given okf-parser 0.45.6 doesn't enforce the AgentRun CHECK constraints, bump the pinned okf-parser version or build project-owned completeness tooling?"
choice: "Build a project-owned `missing_agent_run_fields` checker in scripts/check_agent_run_completeness.py, covered by pytest."
rationale: "docs/rfc/0015 explicitly rejects a mobile okf-parser version pin ('esta RFC não autoriza faixa de versão móvel'), and there is no evidence a newer release within the pinned range (>=0.45.4,<0.46) enforces CHECK constraints during check/compile_types. A small, tested, project-owned check is immediately actionable this round, keeps the hourly loop's validation self-contained, and does not require an untested dependency bump."
---

# Decisão: checador próprio em vez de mudar a dependência

Fecha o gap agora, sem depender de uma versão futura do okf-parser.
