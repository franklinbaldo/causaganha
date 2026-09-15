---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6d5vnd-evidence-pr-opened"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1501"
summary: "PR #1501 aberta a partir de claude/exciting-mccarthy-6d5vnd para main: feat(consolidate): confirm covering index unnecessary with real data (#1468, #1469). Um commit de correção (060b1b1) foi necessário: a validação de completude do AgentRun (scripts/check_agent_run_completeness.py, job 'validate' da CI) acusou 'kind' como ausente nas duas evidências de benchmark porque usei o valor 'runtime_behavior', que não pertence ao enum de knowledge/okf.schema.sql ('test_red'/'test_green'/'ci'/'diff'/'review'/'runtime'/'issue'/'pr'/'okf'/'other') -- corrigido para 'runtime'. Após o push de correção, os 10 checks da CI (CodeQL, GitGuardian, lint, validate, tests (tjro), web, 4x Analyze) ficaram verdes e mergeable_state=clean."
---

# Evidência: PR aberta

PR #1501: https://github.com/franklinbaldo/causaganha/pull/1501 (head `060b1b1`, base `main`@`87cf5f0`). CI vermelha na primeira revisão (kind enum inválido em 2 evidências do próprio relatório AgentRun), corrigida e reenviada; todos os 10 checks passaram na segunda revisão.
