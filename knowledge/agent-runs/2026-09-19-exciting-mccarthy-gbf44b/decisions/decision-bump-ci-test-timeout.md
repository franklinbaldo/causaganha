---
type: AgentDecision
id: "2026-09-19-exciting-mccarthy-gbf44b-decision-bump-ci-test-timeout"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
question: "PR #1585's tests (tjro) CI job (uv run pytest -q, the whole suite, timeout-minutes: 15) was cancelled twice in a row on the same commit (fadd258, a docs-only follow-up), each time after running the full 15 minutes. Is this a transient flake worth a second re-run, or a real, reproducible problem that needs a code/config fix?"
choice: "Treated it as real after the first re-run reproduced the same outcome (per the babysitting rule: a second failure after one re-run is real, not a flake). Root-caused it by comparing job timing across commits: the first commit's (71aed8d) tests job actually completed successfully at ~13 minutes, right against the 15-minute ceiling. Fixed by bumping the tests job's timeout-minutes from 15 to 25 in .github/workflows/test.yml, with a comment explaining why."
rationale: "The evidence pointed at a structural margin problem, not a code bug: tests/segmenter_dataset scales with the real training corpus size, which issue #1050's entire lineage (23 batches now, this round included) has been deliberately growing every round -- 173 documents as of this PR, up from 167 at the start of this round. A suite that already needs ~13 of a 15-minute budget on a good run will intermittently tip over on a slightly slower CI runner, which is exactly the pattern observed (pass at 13min once, cancel at the 15min ceiling twice on functionally identical code). This is a known, worsening trend documented across the whole #1050 backlog, not a fluke isolated to this commit, and not something a re-run could reliably fix (variance in the pass/fail direction was already exhausted by the two observed data points). Bumping the timeout is the minimal, proportionate fix: it does not skip, disable, or quarantine any test, does not shrink the PR's scope, and does not touch test logic -- it only gives the existing, correct test suite the wall-clock room it now needs. A larger structural fix (splitting the suite, parallelizing, or capping corpus growth) is out of scope for a batch-ingestion PR and would be a #1050/#1047 roadmap decision, not something to bundle here."
---

# Decisao: aumentar o timeout-minutes do job de testes na CI

`tests (tjro)` foi cancelado duas vezes seguidas no mesmo commit
(`fadd258`, so um follow-up de documentacao) apos rodar os 15 minutos
completos do timeout configurado. Antes de tratar como flake e so
re-rodar de novo, comparei o tempo real de execucao entre commits: o
primeiro commit desta PR (`71aed8d`) teve seu job `tests (tjro)`
CONCLUIDO COM SUCESSO, mas levando ~13 minutos de um orcamento de 15 --
uma margem de seguranca de apenas ~13%. As duas tentativas seguintes
(mesmo codigo, so um arquivo de documentacao a mais) bateram no teto de
15 minutos e foram canceladas.

Isso e consistente com o padrao ja documentado extensivamente em
`knowledge/backlog/issue-1050.md`: a suite `tests/segmenter_dataset`
escala com o tamanho do corpus real, que a propria linhagem #1050 vem
aumentando a cada lote (173 documentos apos este lote, vindo de 167).
Um orcamento que ja precisa de 13 dos 15 minutos disponiveis vai
oscilar entre passar e estourar dependendo da velocidade do runner da
vez -- exatamente o que foi observado.

Corrigido aumentando `timeout-minutes` do job `tests` de 15 para 25 em
`.github/workflows/test.yml`, com um comentario explicando o motivo.
Nao alterei nenhuma logica de teste, nao pulei/desabilitei nada, e nao
ampliei o escopo desta PR para uma refatoracao maior da suite (isso e
uma decisao de roadmap de #1050/#1047, nao algo a empacotar numa PR de
ingestao de lote).
