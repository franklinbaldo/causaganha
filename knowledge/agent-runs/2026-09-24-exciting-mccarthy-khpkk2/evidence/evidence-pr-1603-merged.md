---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-khpkk2-evidence-pr-1603-merged"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
goal_id: "2026-09-24-exciting-mccarthy-khpkk2-goal-land-batch26-resolve-stale-1600"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1603"
summary: "#1603 (26o lote real, #1050) mesclada apos 'tests (tjro)' completar com sucesso (11/11 checks verdes, squash 4709458). Merge de main de volta para esta branch produziu 1 conflito real em knowledge/backlog/issue-1050.md::blocking_reason -- ambos os lados (esta rodada e batch26) fizeram append puro sobre o mesmo texto-base, confirmado programaticamente (base e prefixo exato de ambos os lados via comparacao de string em Python) -- resolvido concatenando base + append desta rodada (licao de processo) + append do batch26 (narrativa de ingestao), preservando os dois. Reconfirmado ao vivo pos-merge: document_count 191->193, annotation_count 244->246, scripts/segmenter_governance_status.py em 0m57.4s (sem regressao); uv run ruff/okf-parser/pytest completos verdes."
---

# Evidencia: #1603 mesclada e reconciliada localmente

```
mcp__github__merge_pull_request(pullNumber=1603, merge_method=squash)
-> {"sha":"4709458...","merged":true}

$ git fetch origin main && git merge origin/main
CONFLICT (content): Merge conflict in knowledge/backlog/issue-1050.md
```

Confirmado via Python que o texto-base (merge-base 229f354) e prefixo
exato tanto da versao desta rodada (append da licao de processo, +1695
chars) quanto da versao do batch26 (append da narrativa de ingestao,
+3195 chars) -- nenhuma edicao concorrente no mesmo trecho, apenas dois
appends independentes. Resolvido concatenando `base + append_khpkk2 +
append_my6ovw`, mantendo `unblock_condition`/`status` inalterados e
`last_verified_run_id`/`last_verified_at` apontando para esta rodada
(a que efetivamente reconciliou e reverificou o estado combinado).

Pos-merge, ao vivo:

```
$ uv run python scripts/segmenter_governance_status.py --store data/segmenter
{"document_count": 193, "annotation_count": 246, ...
 "val_ceiling_at_full_adjudication": 29, "test_ceiling_at_full_adjudication": 29}
real  0m57.414s

$ uv run ruff check && uv run ruff format --check
All checks passed! / 454 files already formatted

$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{"conformant": true, "diagnostics": [], "concept_count": 2098, ...}

$ uv run pytest -q
(suite completa, sem falhas)
```
