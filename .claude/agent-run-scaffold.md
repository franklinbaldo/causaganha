---
type: AgentRun
id: ""
started_at: ""
completed_at: ""
branch_at_start: ""
commit_at_start: ""
read_claude_md: false
read_open_issues: false
read_open_prs: false
read_okf_knowledge: false
goals: []
goal_rationale: ""
considered_work: []
selected_work: ""
expected_behavior: ""
entry_state: "new"
target_state: "red"
actions: []
evidence: []
checks: []
result_state: "red"
result_summary: ""
next_move: ""
---

# Agent run

Este arquivo é um scaffold deliberadamente incompleto. Copie-o para `knowledge/agent-runs/<timestamp>-<slug>.md` como primeira ação da rodada e use o check do `okf-parser` como feedback operacional durante a sessão.

```bash
uv run okf-parser check knowledge --relational-schema okf.schema.sql
```

Preencha o relatório à medida que a rodada avança. A validação deve conduzir a leitura do estado do projeto, a definição dos goals, a escolha do trabalho, a produção de evidências e o encerramento da sessão.
