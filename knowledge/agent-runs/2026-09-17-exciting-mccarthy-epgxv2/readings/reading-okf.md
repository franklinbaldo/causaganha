---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-epgxv2-reading-okf"
run_id: "2026-09-17-exciting-mccarthy-epgxv2"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-j2t668/run.md, knowledge/agent-runs/index.md, .claude/hourly-loop.md"
finding: "A tensao AgentRun-vs-Wisk permanece sem reconciliacao do dono humano (escalada uma vez em 2026-09-14, reconfirmada sem mudanca por pelo menos 6 rodadas desde entao). Precedente estabelecido: seguir a instrucao explicita do prompt agendado (scaffold AgentRun) sem reenviar notificacao redundante, verificando estado ao vivo do repositorio antes de escolher trabalho para nao duplicar uma rodada Wisk concorrente. knowledge/backlog/issue-1050.md documenta 13 classes de risco/defeito atraves do lote 15 (document_count=132, val/test ceiling=20/20, verificado ao vivo por esta rodada -- identico ao ultimo valor registrado, confirmando ausencia de avanco concorrente desde j2t668)."
---

# Leitura: conhecimento OKF relevante

## Tensao AgentRun vs. Wisk (recorrente, ja mapeada, nao reescalada)

`knowledge/agent-runs/index.md` e `.claude/hourly-loop.md` tratam o
scaffold AgentRun como legado historico em favor do runtime Wisk para o
loop horario do CausaGanha ("nao crie novos AgentRuns"). O prompt desta
sessao agendada, porem, continua instruindo esse mesmo scaffold como
primeira acao obrigatoria. Pelo menos 6 decisoes anteriores (to0ars,
bueov4, ez5wkn, 6kxfkh, zrek2s, j2t668) enfrentaram exatamente essa
tensao e chegaram a mesma conclusao: seguir a instrucao explicita do
prompt agendado (que tem precedencia declarada pelo proprio
system-reminder desta sessao sobre o comportamento padrao), mas
verificar/escolher trabalho de dominio que nao duplique o que uma rodada
Wisk concorrente ja fez. Nenhum fato novo desta rodada muda essa
avaliacao -- a tensao ja foi escalada uma vez com contexto completo, e o
dono ainda nao reconciliou os dois mecanismos, o que e uma decisao dele
em aberto, nao evidencia de que o agendamento foi descontinuado. Esta
rodada nao reenvia notificacao proativa sobre a tensao em si (repetir a
mesma escalada sem fato novo desperdicaria a atencao do dono), mas
registra a decisao de continuidade como AgentDecision, como toda rodada
anterior.

## Estado real do corpus (verificado ao vivo nesta rodada)

`scripts/segmenter_governance_status.py`: `document_count=132`,
`annotation_count=185`, `val_ceiling=test_ceiling=20`,
`corpus_scale_blocks_floor=true` contra o piso RFC 0012 Sec 5 item 4
(>=30 val, >=30 test). Identico ao ultimo valor registrado por j2t668,
confirmando que nenhuma sessao concorrente (Wisk ou outra) avancou o
corpus entre as duas rodadas -- sem risco de colisao imediata de
selecao de candidatos.

## Scan ao vivo do pool para o lote 16

Um scan proprio desta rodada sobre `data/segmenter_samples/*.jsonl`
(usando os nomes de campo corretos `text`/`info.id`/`info.tribunal`/
`info.tipoDocumento`, filtro Sentenca/Acordao 2500-18000 chars,
excluindo TJRO, deduplicado contra o store real via o padrao
`source_uri` `djen_sample_technique1:batch*:{tribunal}:{id}`) encontrou
**220 candidatos elegiveis e nunca usados**. Os tribunais de menor
`store_count` (TRF6=1, TJSC=1, TJMG=2) nao tem mais candidato elegivel
no pool -- diversidade esgotada para esses tres. No proximo tier
(`store_count=3`): TST, TJPI, TJRN, TJGO, TJPB, TJRR, TRF2, TJMT, TJSE.
Dentre esses, TJRN e TJSE ja nao tem candidato elegivel; os demais tem
volume disponivel (TST=2, TJPI=4, TJGO=9, TJPB=9, TJRR=13, TRF2=21,
TJMT=16). Selecionados para o lote 16: TST (2, esgotando esse tribunal
no processo), TJPI (2 de 4), TJGO (1) e TJPB (1) -- continuando a
estrategia de volume sobre diversidade dos next_move anteriores. Dois
candidatos TST tinham markup `<br>` bruto embutido (4 ocorrencias cada),
limpo com o limpador HTML->texto ja validado do lote 3
(`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`);
nenhum candidato tinha entidades HTML (`&...;`) precisando de
`html.unescape`.
