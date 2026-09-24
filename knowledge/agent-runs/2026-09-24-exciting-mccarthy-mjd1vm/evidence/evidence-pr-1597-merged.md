---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-mjd1vm-evidence-pr-1597-merged"
run_id: "2026-09-24-exciting-mccarthy-mjd1vm"
goal_id: "2026-09-24-exciting-mccarthy-mjd1vm-goal-land-stalled-prs"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1597"
summary: "PR #1597 sincronizada com main (merge limpo de ad49efc), 3 threads de revisao do Codex respondidas citando o commit 16f6729 que ja as corrigia e marcadas resolvidas, CI 11/11 verde no commit final (10c4589), mesclada pelo dono humano (franklinbaldo) as 2026-09-24T13:28:02Z, ~1 minuto apos o ultimo check ficar verde."
---

# Evidência: PR #1597 sincronizada, threads fechadas e mesclada

- `git worktree add /tmp/pr1597 claude/exciting-mccarthy-hyn45b` + `git merge origin/main --no-edit`: merge limpo, sem conflito (main so avancou 1 commit docs-only, `ad49efc`).
- Verificacao ao vivo (grep direto no XML de anotacao) confirmou que as 3 correcoes do Codex ja estavam no conteudo (commit `16f6729`, ja presente no branch antes desta rodada): `valor_condenacao` removido do span `R$ 10.000,00`; `honorarios_fim` ancorado em "valor atualizado da causa" (TJCE) e "valor atualizado da condenação" (TJTO) em vez do ponto final.
- `uv run ruff check` / `uv run ruff format --check`: limpos.
- `uv run pytest -q tests/segmenter_dataset`: 249 passed (100%), EXIT:0 -- rodou ~10 minutos, consistente com a lentidao ja documentada em lotes anteriores neste tamanho de corpus (o fix de performance de #1598 ainda nao estava mesclado no branch de #1597 nesse momento).
- `git push -u origin claude/exciting-mccarthy-hyn45b`: `427560b..10c4589`.
- 3 respostas postadas nas threads do Codex (`discussion_r4057219196`, `_203`, `_207`) citando o commit `16f6729`; `pull_request_review_write resolve_thread` confirmou as 3 threads resolvidas (`PRRT_kwDOOz8pIc6kJ0Ao/At/Ax`).
- CI do commit final (`10c4589`, apos push): 11/11 checks `success` (lint, tests (tjro), archive-cors-proxy, web, validate, CodeQL x4, GitGuardian) -- `tests (tjro)` levou de 13:09:26 a 13:27:37 (~18min, dentro do range historico ja documentado para esta suite nesta escala).
- `pull_request_read get`: `state: closed`, `merged: true`, `merged_by: franklinbaldo`, `merged_at: 2026-09-24T13:28:02Z`.
