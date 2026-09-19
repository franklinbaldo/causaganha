---
type: AgentReading
id: "2026-09-19-exciting-mccarthy-gbf44b-reading-okf"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/index.md"
finding: "knowledge/backlog/issue-1050.md documenta 21 lotes reais e 16 classes de risco de processo/anotacao ja conhecidas (nenhuma e bug de codigo de producao pendente, exceto a classe 5 ja corrigida). last_verified_run_id aponta para o lote Wisk 21 (167 documentos, teto val/test 25/25). knowledge/agent-runs/index.md e .claude/hourly-loop.md marcam o mecanismo AgentRun como legado para o loop horario (Wisk e o runtime atual), mas o BacklogItem nao esta na lista de tipos descontinuados e o prompt agendado desta sessao especifica ainda instrui explicitamente o scaffold AgentRun -- tensao ja escalada uma vez (to0ars, 2026-09-14) e reconfirmada sem mudanca por 6+ rodadas subsequentes."
---

# Leitura: conhecimento OKF relevante

`knowledge/backlog/issue-1050.md` (BacklogItem, `status: unblocked`) e o
registro operacional mais denso da linhagem: 21 lotes historiados em
prosa contigua no campo `blocking_reason`, com contagens de
`document_count`/teto val-test por lote e 16 classes de risco numeradas
(concorrencia entre sessoes, HTML bruto/entidades nao decodificadas,
substituicao NBSP->espaco, pares sem cue de fechamento vs. sub-anotacao
com cue disponivel, TRF4 descartado por colapsar abaixo do piso de 2500
caracteres pos-limpeza, etc.). `last_verified_run_id` aponta para o lote
Wisk mais recente (`20260917T082642Z`, lote 21, 167 documentos, teto
val/test 25/25) -- consistente com o estado ao vivo confirmado nesta
rodada via `scripts/segmenter_governance_status.py`.

`knowledge/agent-runs/index.md` e `.claude/hourly-loop.md` declaram o
mecanismo `AgentRun`/`AgentReading`/`AgentGoal`/`AgentDecision`/
`AgentEvidence`/`AgentCheck` legado para o loop horario, substituido
pelo runtime Wisk (`.wisk/knowledge/`). `BacklogItem` (usado por
`knowledge/backlog/issue-1050.md`) nao esta nessa lista de tipos
descontinuados, entao continua sendo atualizado por qualquer mecanismo.
A tensao entre "nao crie novos AgentRuns" (guia do repositorio) e o
prompt agendado desta sessao (que instrui explicitamente criar o
relatorio a partir de `.claude/agent-run-scaffold.md`) ja foi escalada
uma vez via notificacao (rodada to0ars, 2026-09-14) e reconfirmada sem
fato novo por pelo menos 6 rodadas subsequentes (zrek2s, 83kr8s,
hv2ep2, imy2ed, 5lvbii, j2t668, epgxv2) -- nao ha fato novo nesta
rodada que justifique reabrir a escalada.

`knowledge/index.md` descreve o bundle OKF geral (fontes/pipelines
tipados, checagem relacional via `okf-parser`) -- camada separada dos
datasets arquivados (Parquet/DuckDB), sem relacao direta com a
linhagem #1050.
