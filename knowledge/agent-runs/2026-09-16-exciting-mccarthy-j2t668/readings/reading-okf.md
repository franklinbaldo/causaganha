---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-j2t668-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-{zrek2s,uyx7xc,mg2tp1}/run.md, knowledge/agent-runs/index.md"
finding: "AgentRun-vs-Wisk tension is longstanding (5+ prior decisions since 2026-09-14) and already escalated once; precedent is to follow the scheduled prompt's explicit scaffold instruction while verifying live repository state to avoid duplicating concurrent Wisk work, and this round follows that precedent again -- no new fact reopens the tension for a fresh escalation. knowledge/backlog/issue-1050.md documents 14 risk/defect classes through batch14, including the newest (risk class 12): two independent sessions can scan the same pool live, tie on the same lowest-store_count tribunal, and pick the same candidate without either session's own dedup catching it, surfacing only as a dirty mergeable_state or a silent merge after the first PR lands (exactly what happened between #1565/batch13 and #1567/batch14, and again between #1567 and the now-closed duplicate #1568). Corpus growth is at document_count=126 (verified live), 218 eligible never-used real candidates remain in data/segmenter_samples/*.jsonl across 17 tribunals (verified live with a corrected field-name scan -- prior rounds' 'pool nearly exhausted' framing referred to new-tribunal diversity, not remaining candidate volume, which is still substantial)."
---

# Leitura: conhecimento OKF relevante

## Tensao AgentRun vs. Wisk (recorrente, ja mapeada)

`knowledge/agent-runs/index.md` trata o scaffold AgentRun como legado em
favor do runtime Wisk, mas o prompt desta sessao agendada continua
instruindo, sem ressalva, o mesmo scaffold legado como primeira acao
obrigatoria. Pelo menos 5 decisoes anteriores (to0ars, bueov4, ez5wkn,
6kxfkh, zrek2s) enfrentaram exatamente essa tensao e chegaram a mesma
conclusao: seguir a instrucao explicita do prompt agendado (que tem
precedencia declarada pelo proprio system-reminder desta sessao), mas
escolher/verificar trabalho de dominio que nao duplique o que uma rodada
Wisk concorrente ja fez. Nenhum fato novo desta rodada muda essa
avaliacao -- a tensao ja foi escalada uma vez (to0ars, 2026-09-14) com
contexto completo, e o dono ainda nao reconciliou os dois mecanismos, o
que e uma decisao dele em aberto, nao evidencia de que o agendamento foi
descontinuado.

## Estado real do corpus (verificado ao vivo nesta rodada)

`scripts/segmenter_governance_status.py`: `document_count=126`,
`annotation_count=179`, `val_ceiling=test_ceiling=19`,
`corpus_scale_blocks_floor=true` contra o piso RFC 0012 Sec 5 item 4
(>=30 val, >=30 test). `knowledge/backlog/issue-1050.md` esta atualizado
ate o lote 14 (Wisk), incluindo uma 12a classe de risco nova: duas
sessoes escaneando o mesmo pool ao vivo podem empatar no mesmo tribunal
de menor `store_count` e escolher o MESMO candidato sem que o dedup de
nenhuma das duas detecte -- exatamente o padrao que gerou a colisao
#1565/#1567 e, nesta rodada, a duplicata agora fechada #1568.

## Achado novo desta rodada: o pool de candidatos NAO esta perto de se
esgotar

Um scan ao vivo de `data/segmenter_samples/*.jsonl` (script proprio desta
rodada, usando os nomes de campo corretos `text`/`info.id`, nao
`texto_limpo`/`id_documento` como um scan anterior mal-escrito teria
sugerido) encontrou **218 candidatos reais, elegiveis e nunca usados**
(Sentenca/Acordao, 2500-18000 chars, excluindo TJRO, excluindo pares
`(tribunal, id)` ja no store) distribuidos por 17 tribunais. Os tribunais
com menor `store_count` (2 cada): TST, TJRJ, TJTO, TRF2 -- todos com
candidatos elegiveis disponiveis (TJRJ tem 49 candidatos ainda nao
usados, TJTO 28, TRF2 22, TST 3). TRF6 e TJSC (store_count=1 cada) NAO
tem mais candidatos elegiveis no pool -- diversidade de tribunal esta
esgotada para esses dois especificamente, mas o pool geral de volume
esta longe de esgotado. Isso confirma que a estrategia certa para esta
rodada e a mesma dos next_move anteriores: crescer volume nos tribunais
de menor `store_count` ja representados, nao buscar diversidade de
tribunal nova.
