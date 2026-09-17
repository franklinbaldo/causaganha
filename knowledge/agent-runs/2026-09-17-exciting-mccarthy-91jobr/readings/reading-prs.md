---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-91jobr-reading-prs"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
subject: "open_prs"
reference: "github pull requests (list_pull_requests, state=open, franklinbaldo/causaganha)"
finding: "3 PRs abertas: #1578 (Wisk, closeout do lote 18, fora do escopo desta sessao), #1576 (AgentRun, sessao 726qh5, 6 documentos reais anotados de #1050 ja stale contra main pos-#1577) e #1353 (dependabot, sem relacao). #1576 rebase limpo (git merge-tree) contra origin/main atual: os 6 pares documento/anotacao XML sao adicoes puras sem conflito; os unicos 4 marcadores de conflito reais estao em dois arquivos de evidencia de auditoria (docs/planning/evidence/segmenter-djen-sample-batch18-{candidates,overrides}.json) que colidem apenas de NOME com os equivalentes ja commitados por #1577."
---

# Leitura: PRs abertas

`mcp__github__list_pull_requests` (state=open) retornou 3 PRs:

- **#1578** ("wisk(run): confirm PR #1577 merge, close out round report")
  -- aberta pelo runtime Wisk as 2026-09-17T04:19Z, docs-only
  (`.wisk/knowledge/experiences/runs/`). Nao criada por esta sessao, fora
  do escopo desta rodada (regra de nao administrar PRs de outro
  mecanismo/autor sem pedido explicito).
- **#1576** ("feat(segmenter): ingest eighteenth real multi-tribunal
  batch via Technique 1 (#1050)") -- aberta pela sessao AgentRun anterior
  `726qh5` as 2026-09-17T03:30Z, branch `claude/exciting-mccarthy-726qh5`,
  base `main@38daed4` (ja superada por `main@0a831be`, que mesclou o
  batch 18 concorrente da PR #1577/Wisk primeiro).
  `git fetch` + `git merge-tree $(git merge-base origin/main
  origin/claude/exciting-mccarthy-726qh5) origin/main
  origin/claude/exciting-mccarthy-726qh5` confirma que os 6 pares
  `data/segmenter/documents/*.xml` +
  `data/segmenter/annotations/*/*.xml` desta PR sao adicoes puras (sem
  overlap de IDs com o que #1577 ja mesclou) -- nenhum conflito real na
  carga de dados. Os 4 marcadores de conflito genuinos do merge-tree
  estao inteiramente em dois arquivos de evidencia de auditoria com nome
  fixo por batch (`docs/planning/evidence/segmenter-djen-sample-batch18-
  candidates.json` e `...-overrides.json`) -- ambas as PRs escolheram o
  mesmo numero de lote ("18") e portanto o mesmo nome de arquivo,
  causando colisao puramente de nomenclatura, nao de conteudo de dominio.
  Branch policy desta sessao (`.claude/agent-run-scaffold.md` +
  instrucoes operacionais) impede push direto em
  `claude/exciting-mccarthy-726qh5` (branch de outra sessao) sem permissao
  explicita -- a decisao desta rodada e resgatar o conteudo real (6
  documentos/anotacoes) aplicando o mesmo diff sobre a branch propria
  desta sessao, renumerando para "lote 19", em vez de reescrever a branch
  alheia.
- **#1353** (dependabot, `deployment/relay-cf`) -- sem relacao com
  trabalho de dominio, reconfirmada de rodadas anteriores.
