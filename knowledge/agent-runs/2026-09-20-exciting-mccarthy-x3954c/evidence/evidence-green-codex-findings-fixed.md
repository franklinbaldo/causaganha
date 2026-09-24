---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-x3954c-evidence-green-codex-findings-fixed"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
kind: "test_green"
reference: "uv run pytest -q tests/segmenter_dataset/test_dedup.py (10 testes) e uv run pytest -q tests/segmenter_dataset (suite completa), apos substituir a formula de divisao por uma comparacao direta sem divisao e adicionar o desempate por ordem de insercao"
summary: "Todos os 10 testes de tests/segmenter_dataset/test_dedup.py (incluindo os 4 novos que reproduziam os achados do Codex) passam apos a correcao. Suite completa tests/segmenter_dataset: 100% verde. Runtime real no corpus de producao reconfirmado apos a correcao: scripts/segmenter_governance_status.py em 1m6.885s (praticamente identico aos 1m6.470s medidos antes desta correcao adicional), com saida identica (document_count=191, val_ceiling=test_ceiling=29) -- confirma que corrigir os 3 achados do Codex nao reintroduziu o gargalo de desempenho."
---

# Evidência: GREEN — achados do Codex corrigidos, desempenho preservado

```
$ uv run pytest -q tests/segmenter_dataset/test_dedup.py
..........                                                               [100%]

$ uv run pytest -q tests/segmenter_dataset
........................................................................ [ 18%]
........................................................................ [ 36%]
........................................................................ [ 55%]
........................................................................ [ 73%]
........................................................................ [ 92%]
...............................                                          [100%]

$ time uv run python scripts/segmenter_governance_status.py
{ ... "document_count": 191, ... "val_ceiling_at_full_adjudication": 29, "test_ceiling_at_full_adjudication": 29, ... }
real	1m6.885s
```

O runtime pós-correção (1m6.885s) é essencialmente idêntico ao medido
imediatamente após a primeira versão da poda (1m6.470s) — a correção
dos 3 achados do Codex (troca da fórmula de divisão por uma comparação
direta sem divisão, mais o desempate de ordem) não reintroduziu
nenhuma regressão de desempenho.
