---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-96cgqx-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-zrek2s/run.md, knowledge/agent-runs/index.md, .claude/hourly-loop.md"
finding: "knowledge/backlog/issue-1050.md esta atualizado (last_verified_run_id=5lvbii, lote 12, document_count=121) e documenta 10 classes de risco/defeito ja mapeadas -- todas relevantes para o 13o lote. A tensao AgentRun-vs-Wisk (knowledge/agent-runs/index.md e .claude/hourly-loop.md declaram o scaffold AgentRun legado) continua sem reconciliacao do dono humano e ja foi escalada uma vez (2026-09-14); nenhum fato novo justifica reescalar. Mantida a decisao de 5+ rodadas anteriores: seguir o scaffold desta sessao agendada (instrucao explicita tem precedencia), escolher trabalho de dominio que nao duplique rodadas Wisk/AgentRun concorrentes, verificando o estado real ao vivo antes de selecionar candidatos."
---

# Leitura: conhecimento OKF relevante

## `knowledge/backlog/issue-1050.md` (lido integralmente)

Documenta a historia completa dos doze lotes ja mesclados hoje, dez
classes de risco/defeito numeradas (pares sem cue de fechamento,
entidades HTML, markup bruto embutido, NBSP disfarcado, o bug de
`str.strip()` corrigido no lote 7, CRLF, caracteres de controle ASCII,
dedup por hash errado durante selecao, dedup por hash errado desde o
inicio, colisao de `--tagged-dir` com arquivos-fonte). `last_verified_run_id`
aponta para a rodada `5lvbii` (lote 12), com `document_count=121`,
consistente com a verificacao ao vivo desta rodada via
`scripts/segmenter_governance_status.py`. Estado: `status: "unblocked"`,
proxima faixa de tribunais por volume (menor `store_count`): TJRJ, TJSE,
TJMG, TRF5, TJRS, TRF2, TJTO (TJES/TJGO, usados no lote 12, devem ter
subido para `store_count=3`).

## Tensao AgentRun vs. Wisk (reconfirmada, nenhum fato novo)

`knowledge/agent-runs/index.md` e `.claude/hourly-loop.md` continuam
declarando o mecanismo `AgentRun`/scaffold legado em favor do runtime
Wisk para o loop horario. O prompt desta sessao agendada continua
instruindo, sem ressalva, o mesmo scaffold legado como primeira acao da
rodada. Cinco decisoes anteriores (to0ars, bueov4, ez5wkn, 6kxfkh,
zrek2s) ja enfrentaram exatamente essa tensao e chegaram a mesma
conclusao: seguir a instrucao explicita do prompt agendado (que tem
precedencia declarada pelo system-reminder desta sessao), mas escolher
trabalho de dominio que nao compita nem duplique trabalho Wisk ativo, e
nao reescalar a tensao em si sem fato novo (ja escalada uma vez,
2026-09-14). Nenhum fato novo nesta leitura muda essa conclusao -- mantida
sem reescalar.
