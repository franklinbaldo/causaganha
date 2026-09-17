---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-726qh5-reading-okf"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-17-exciting-mccarthy-epgxv2/run.md, knowledge/okf.schema.sql"
finding: "knowledge/backlog/issue-1050.md e o cache durável do dominio (nao preso ao ciclo de vida de uma rodada) e documenta 16 lotes mesclados com 14 classes de risco numeradas; a rodada anterior (epgxv2, lote 16) confirmou document_count=138/annotation_count=191/val_ceiling=test_ceiling=21 ao vivo e ja apontou o proximo tier de tribunais por menor store_count (TJGO/TJPB subindo de tier, TJRR/TRF2/TJMT ainda com volume alto). O schema relacional (knowledge/okf.schema.sql) fixa os seis types da sessao de agente (AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck) e os demais conceitos de dominio (BacklogItem, contratos de fonte/pipeline/projecao) sem exigir mudanca de schema para o trabalho desta rodada."
---

# Leitura: conhecimento OKF relevante

`knowledge/` tem seis diretorios de dominio: `backlog/` (fatos que
sobrevivem a rodadas individuais), `agent-runs/` (relatorios por
sessao), `contracts/`, `pipelines/`, `projections/` e `sources/`
(modelo de dados do produto -- DocumentoProcesso, Processo, fontes
DJEN/JURIS/STJ/DataJud etc., nenhum tocado por esta rodada).

`knowledge/backlog/issue-1050.md` e a leitura central para o trabalho
desta rodada: registra, como `BacklogItem` (`status: unblocked`), a
historia completa dos 16 lotes ja mesclados via
`scripts/ingest_djen_sample_technique1_batch.py`, 14 classes de risco
numeradas (HTML bruto/entidades nao decodificadas por tribunal,
substituicao NBSP->espaco pervasiva, pares sem cue de fechamento
legitimos vs. sub-anotacao com cue disponivel, deduplicacao por
content_hash+(tribunal,id) em vez de campo de hash externo, colisao de
candidatos entre sessoes concorrentes, campo `info.tribunal` em branco
para `tjsc_acordao.jsonl`, nomes de campo corretos no pool
`text`/`info.id`/`info.tribunal`/`info.tipoDocumento`) e o proximo
passo esperado (continuar por volume, tribunais de menor
`store_count`). `last_verified_run_id: 2026-09-17-exciting-mccarthy-epgxv2`,
`last_verified_at: 2026-09-17T01:20:00Z` -- recente o suficiente para
nao exigir reinvestigacao completa, apenas uma reverificacao ao vivo
via `scripts/segmenter_governance_status.py` antes de selecionar
candidatos (em andamento nesta rodada).

`knowledge/agent-runs/2026-09-17-exciting-mccarthy-epgxv2/run.md` (a
rodada imediatamente anterior nesta linhagem) fechou com
`result_state: merged` (PR #1572) e `next_move` apontando exatamente
para o padrao que esta rodada segue: reescanear
`data/segmenter_samples/*.jsonl` ao vivo, verificar HTML
nao-decodificado/markup bruto antes de anotar, e verificar cues de
fechamento genuinas antes de declarar overrides (classe de risco 14).

`knowledge/okf.schema.sql` fixa os seis types de sessao de agente
(`AgentRun`, `AgentReading`, `AgentGoal`, `AgentDecision`,
`AgentEvidence`, `AgentCheck`) com seus campos obrigatorios/opcionais;
nao ha necessidade de estender o modelo OKF nesta rodada -- o
`BacklogItem` ja captura bem o estado de dominio entre rodadas, e o
trabalho selecionado (mais um lote real do corpus) cabe integralmente
nos types existentes.
