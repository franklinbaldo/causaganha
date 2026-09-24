---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-khpkk2-evidence-issue-1050-lesson-forwarded"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
goal_id: "2026-09-24-exciting-mccarthy-khpkk2-goal-land-batch26-resolve-stale-1600"
kind: "diff"
reference: "git diff knowledge/backlog/issue-1050.md (branch claude/exciting-mccarthy-khpkk2 vs origin/claude/exciting-mccarthy-mjd1vm); PR #1600"
summary: "Confirmado por git diff local (apos git fetch origin claude/exciting-mccarthy-mjd1vm) que o unico conteudo de dominio de #1600 ainda ausente de main e um append ao campo blocking_reason de knowledge/backlog/issue-1050.md, registrando a licao de processo: uma correcao pushada nao fecha sozinha a thread de revisao do Codex, alguem precisa responder/resolver explicitamente. Exatamente 3 linhas mudam (o campo blocking_reason mais last_verified_run_id/last_verified_at), sem nenhum outro arquivo de dominio divergente. Aplicado diretamente em main via esta rodada, sem herdar os outros 12 arquivos redundantes do relatorio AgentRun mjd1vm."
---

# Evidencia: licao de processo de #1600 preservada diretamente

```
$ git fetch origin claude/exciting-mccarthy-mjd1vm --quiet
$ git show origin/claude/exciting-mccarthy-mjd1vm:knowledge/backlog/issue-1050.md > /tmp/issue-1050-mjd1vm.md
$ diff knowledge/backlog/issue-1050.md /tmp/issue-1050-mjd1vm.md
6c6
< blocking_reason: "... batch25 pos-revisao (PR #1597, mesclada ...)."
---
> blocking_reason: "... batch25 pos-revisao (PR #1597, mesclada ...).
> ... licao de processo: uma correcao pushada nao fecha a thread de
> revisao sozinha, alguem (humano ou agente) precisa
> responder/resolver explicitamente, e isso pode ficar pendente por
> dias mesmo com CI verde. ..."
last_verified_run_id/last_verified_at atualizados de fv62kx/2026-09-20
para mjd1vm/2026-09-24T13:28:02Z.
```

Nenhum outro arquivo de dominio (fora do proprio relatorio
`AgentRun` `mjd1vm`) diverge entre `main` e o branch de `#1600`. O
conteudo foi copiado para `knowledge/backlog/issue-1050.md` nesta
rodada (`cp /tmp/issue-1050-mjd1vm.md knowledge/backlog/issue-1050.md`)
e commitado junto com o relatorio desta rodada.

Correcao adicional necessaria: `last_verified_run_id`/`last_verified_at`
vieram do arquivo copiado apontando para `2026-09-24-exciting-mccarthy-mjd1vm`,
cujo relatorio `AgentRun` nunca foi mesclado (a PR #1600 que o carregava
foi fechada, nao mesclada -- ver decision-close-1600-forward-lesson).
`tests/knowledge/test_backlog.py::test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round`
pegou isso ao vivo (`AssertionError` apontando para um `run.md`
inexistente). Corrigido apontando esses dois campos para esta propria
rodada (`khpkk2`), que e quem de fato aplicou a verificacao em `main`.
`uv run pytest -q` (suite completa) 100% verde apos a correcao.
