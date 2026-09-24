---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-x3954c-evidence-pr-1598-merged"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1598, squash-mesclada em main como commit 6d2ac9a"
summary: "PR #1598 mesclada por franklinbaldo em 2026-09-24 (evento pull_request.closed com outcome=merged, sessao automaticamente desinscrita). Confirmado ao vivo via git fetch origin main: main avancou de 4a3dd9c para 6d2ac9a com a mensagem 'fix(segmenter): eliminate O(n^2) unpruned near-duplicate scan in dedup.py (#1598)'. git show origin/main:src/segmenter_dataset/dedup.py confirma a comparacao direta sem divisao (2*length_a >= threshold*(length_a+lengths[j])) presente no main mesclado. knowledge/agent-runs/2026-09-20-exciting-mccarthy-x3954c/ (este relatorio) sobreviveu ao squash merge intacto; uv run okf-parser check knowledge reconfirmado com 0 diagnosticos apos reiniciar o branch local a partir de origin/main."
---

# Evidência: PR #1598 mesclada

- Notificação `pull_request.closed` (`outcome: "merged"`, `pr:
  "franklinbaldo/causaganha#1598"`) recebida em 2026-09-24T14:00:35Z, 4
  dias depois da abertura da PR nesta mesma sessão contínua (o
  intervalo é o tempo real de espera por revisão humana, não uma
  regressão desta rodada).
- `git fetch origin main`: `4a3dd9c..6d2ac9a main -> origin/main`,
  commit `6d2ac9a` = `"fix(segmenter): eliminate O(n^2) unpruned
  near-duplicate scan in dedup.py (#1598)"`.
- `git show origin/main:src/segmenter_dataset/dedup.py | grep "2 \*
  length_a >= threshold"` confirma a linha da correção presente no
  `main` mesclado.
- Branch local reiniciado a partir de `origin/main` (squash merge, não
  fast-forward — a mesma convenção já seguida por rodadas anteriores
  quando uma PR delas é mesclada por squash).
