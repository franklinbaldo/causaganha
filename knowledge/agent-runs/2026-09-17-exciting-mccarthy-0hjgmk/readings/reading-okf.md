---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-0hjgmk-reading-okf"
run_id: "2026-09-17-exciting-mccarthy-0hjgmk"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-17-exciting-mccarthy-epgxv2/run.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-14-exciting-mccarthy-to0ars/decisions/decision-agentrun-vs-wisk-policy-conflict.md"
finding: "A tensao AgentRun-vs-Wisk permanece sem reconciliacao do dono humano (escalada uma vez em 2026-09-14 via notificacao proativa; reconfirmada sem mudanca por pelo menos 7 rodadas desde entao, incluindo esta). Precedente mantido: seguir a instrucao explicita do prompt agendado sem reenviar notificacao redundante. knowledge/backlog/issue-1050.md documenta 14 classes de risco/defeito atraves do lote 16 (document_count=138, val/test ceiling=21/21, verificado ao vivo por esta rodada). Um scan proprio do pool (data/segmenter_samples/*.jsonl, filtrando por uri djen_sample_technique1: no store) encontrou 163 candidatos elegiveis e nunca usados, com TJBA/TJMA/TJCE no tier de menor store_count (3) entre tribunais com candidatos disponiveis."
---

# Leitura: conhecimento OKF relevante

## Tensao AgentRun vs. Wisk (recorrente, ja mapeada, nao reescalada)

`.claude/hourly-loop.md` trata o scaffold AgentRun como legado historico
em favor do runtime Wisk para o loop horario ("nao crie novos
AgentRuns"). O prompt desta sessao agendada continua instruindo esse
scaffold como primeira acao obrigatoria. A decisao
`2026-09-14-exciting-mccarthy-to0ars-decision-agentrun-vs-wisk-policy-conflict`
ja escalou esse exato conflito via notificacao proativa ao dono do
repositorio; pelo menos 6 rodadas desde entao (bueov4, ez5wkn, 6kxfkh,
zrek2s, j2t668, epgxv2) reconfirmaram a mesma decisao sem fato novo. Esta
rodada segue o mesmo precedente: cumprir o scaffold como instruido
(prompt agendado tem precedencia declarada), sem reenviar a mesma
notificacao (nao ha fato novo que justifique gastar a atencao do dono de
novo).

## Estado real do corpus (verificado ao vivo nesta rodada)

`scripts/segmenter_governance_status.py`: `document_count=138`,
`annotation_count=191`, `review_count=31`, `val_ceiling=test_ceiling=21`,
`corpus_scale_blocks_floor=true` contra o piso RFC 0012 Sec 5 item 4
(>=30 val, >=30 test). Identico ao ultimo valor registrado pelo lote 16
(epgxv2), confirmando que nenhuma sessao concorrente avancou o corpus
desde entao.

## Scan ao vivo do pool para o lote 17

Um scan proprio desta rodada sobre `data/segmenter/documents/*.xml`
(extraindo `uri="djen_sample_technique1:batchN:TRIBUNAL:ID"` do atributo
`source` para construir o conjunto de chaves ja usadas -- 77 documentos
dessa fonte especifica, dos 138 totais no store; os demais 61 vem de
`juris_expansion`/`juris_technique1_batch1`/`round_e`/`round_f`/
`rounds_abcd_unattributed`/`seed`, fora do escopo desta linhagem) contra
`data/segmenter_samples/*.jsonl` (nomes de campo corretos
`text`/`info.id`/`info.tribunal`/`info.tipoDocumento`, filtro
Sentenca/Acordao 2500-18000 chars, excluindo TJRO) encontrou **163
candidatos elegiveis e nunca usados** nesta fonte. `store_count` por
tribunal (menor primeiro, apenas djen_sample_technique1): TJSC=1,
TRF6=1 (sem candidato elegivel restante -- pool exaurido), TJMG=2 (sem
candidato elegivel restante), depois o tier `store_count=3`: TJCE,
TJMT, TRF5, TRF4, TJSE, TJBA, TRF2, TJMA, TRF3, TJES, TJRN, TJRS, TJRR
-- dos quais TJRN e TJRS ja nao tem candidato elegivel, mas TJBA (2
candidatos), TJMA (4), TJCE (5), TRF5 (19), TRF2 (21), TJMT (16), TJRR
(13), TRF3 (10), TJES (7) ainda tem. Selecionados para o lote 17: TJBA
(2, esgotando esse tribunal), TJMA (2 de 4, os dois mais curtos) e TJCE
(2 de 5, os dois mais curtos) -- continuando a estrategia de volume
sobre diversidade dos `next_move` anteriores, priorizando os tribunais
de menor `store_count` com poucos candidatos restantes (TJBA) antes dos
de maior volume disponivel (TRF2/TRF5/TJMT/TJRR), para nao deixar um
pool pequeno cada vez mais dificil de esgotar completamente em uma
rodada futura. TJBA e TJCE tem NBSP (U+00A0) genuino embutido no texto
fonte (20/15 e 12/4 ocorrencias respectivamente) -- risco ja mapeado
(classe 13); os dois candidatos TJMA selecionados nao tem NBSP nem
markup HTML embutido.
