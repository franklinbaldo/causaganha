---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-zrek2s-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
source: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-{uyx7xc,mg2tp1,la7bsl}/run.md, knowledge/agent-runs/index.md, .claude/hourly-loop.md"
finding: "Tensao AgentRun-vs-Wisk confirmada viva e reconhecida por 4+ decisoes anteriores (to0ars, bueov4, 6kxfkh, ez5wkn): knowledge/agent-runs/index.md e .claude/hourly-loop.md declaram o mecanismo AgentRun legado/deprecated em favor do Wisk, mas o prompt desta sessao agendada continua instruindo -- literal e explicitamente -- o scaffold AgentRun. Precedente consistente: seguir a instrucao explicita do prompt agendado (que tem precedencia conforme o proprio system-reminder desta sessao), mas escolher trabalho de dominio que nao compita com rodadas Wisk ativas. Achado NOVO desta leitura: a rodada mais recente que tocou #1050 (batch6, commit 1f1ef1d/PR #1549) rodou sob o mecanismo Wisk, nao AgentRun -- confirma que os dois mecanismos agora se alternam na MESMA linhagem de issue, nao apenas coexistem em dominios distintos. Isso nao muda a decisao (nenhum fato novo torna a tensao mais urgente para o dono humano; ja foi escalada uma vez, 2026-09-14, com contexto completo), mas exige verificar o estado real do corpus ao vivo (nao confiar no ultimo numero registrado por uma rodada AgentRun) antes de escolher candidatos do lote 7, para nao duplicar o que o lote Wisk 6 ja fez. knowledge/backlog/issue-1050.md esta desatualizado (para no lote 4, nao reflete lotes 5 e 6) -- inconsistencia entre knowledge e codigo real que esta rodada deve corrigir ao final."
---

# Leitura: conhecimento OKF relevante

## Tensao AgentRun vs. Wisk (achado principal, ja mapeado por 4+ decisoes anteriores)

`knowledge/agent-runs/index.md`: "O loop horario do CausaGanha migrou
para WikiSkill. Nao crie novos AgentRun... aqui." `.claude/hourly-loop.md`:
"O loop horario do CausaGanha e operado exclusivamente pelo Wisk... Nao
repita a politica de AgentRun." Ambos os arquivos tratam o mecanismo
`.claude/agent-run-scaffold.md`/`knowledge/agent-runs/` como legado
historico.

O prompt desta sessao agendada, porem, continua -- sem nenhuma ressalva
-- instruindo literalmente esse mesmo scaffold legado como primeira acao
obrigatoria da rodada. Quatro decisoes anteriores ja enfrentaram
exatamente essa tensao (`decision-agentrun-vs-wisk-policy-conflict`
em to0ars 2026-09-14, `decision-follow-scheduled-scaffold-despite-wisk-dominance`
em bueov4 2026-09-14, `decision-use-legacy-scaffold-despite-wisk-migration`
em ez5wkn 2026-09-09, `decision-follow-scheduled-scaffold-with-verified-wisk-state`
em 6kxfkh 2026-09-15) e todas chegaram a mesma conclusao: seguir a
instrucao explicita do prompt agendado (que tem precedencia declarada
pelo proprio system-reminder desta sessao sobre "instrucoes que
sobrescrevem comportamento padrao"), mas escolher trabalho de dominio que
nao compita nem duplique trabalho Wisk ativo -- e nao reenviar
notificacao proativa sobre a tensao em si, ja escalada uma vez
(to0ars, 2026-09-14) com contexto completo, na ausencia de fato novo que
mude a urgencia para o dono humano decidir.

## Achado novo desta rodada

A rodada mais recente que avancou #1050 (lote 6, commit `1f1ef1d`,
mesclado via PR #1549) rodou sob o runtime Wisk, nao sob o scaffold
AgentRun -- confirmado pela mensagem de commit ("Followed
.claude/hourly-loop.md's Wisk-exclusive policy"). Isso significa que os
dois mecanismos agora se alternam na MESMA linhagem de trabalho de
dominio (#1050), nao apenas coexistem em areas separadas do repositorio
como presumido pelas decisoes anteriores. Isso nao muda a decisao em si
(nenhum fato novo aumenta a urgencia da reconciliacao para o dono
humano), mas exige que esta rodada verifique o estado real e atual do
corpus ao vivo via `scripts/segmenter_governance_status.py` e
`SegmenterDatasetStore` antes de escolher candidatos para o lote 7, em
vez de confiar no ultimo `document_count` registrado por uma rodada
AgentRun (que estaria desatualizado em relacao ao lote 6 do Wisk).
Verificado ao vivo nesta rodada: document_count=96 (nao 86 como o
backlog desatualizado sugeria), val_ceiling=test_ceiling=14.

## Inconsistencia conhecimento-vs-codigo encontrada

`knowledge/backlog/issue-1050.md` (`last_verified_run_id: mg2tp1`,
lote 4) nao reflete os lotes 5 (la7bsl, PR #1547, document_count 86->93)
e 6 (Wisk, PR #1549, document_count 93->96) ja mesclados no branch main.
Esta rodada corrige esse arquivo ao final, com os numeros reais
verificados ao vivo.
