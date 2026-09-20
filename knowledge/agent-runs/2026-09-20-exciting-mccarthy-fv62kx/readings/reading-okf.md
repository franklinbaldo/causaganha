---
type: AgentReading
id: "2026-09-20-exciting-mccarthy-fv62kx-reading-okf"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-19-exciting-mccarthy-gbf44b/run.md, knowledge/agent-runs/index.md"
finding: "knowledge/backlog/issue-1050.md documenta 23 lotes reais e 17 classes de risco (a mais recente, 17, e exatamente o bug que a PR concorrente #1588 esta corrigindo em codigo). O relatorio AgentRun anterior (gbf44b, 2026-09-19) fechou verde com document_count=173/val-test 26/26 e apontou como next_move reescanear ao vivo data/segmenter_samples/*.jsonl para o proximo tier de menor store_count -- ja parcialmente superado pelo lote 23 (#1586, mesclado depois de gbf44b) que levou o corpus a 179/27/27. A tensao AgentRun-vs-Wisk (relatada em to0ars, 2026-09-14) permanece sem reconciliacao do dono humano apos 7+ rodadas subsequentes sem fato novo; nao sera reescalada de novo nesta rodada."
---

# Leitura: conhecimento OKF relevante

`knowledge/backlog/issue-1050.md` (BacklogItem, `status: unblocked`)
continua o registro operacional mais denso da linhagem: agora 23 lotes
historiados, incluindo o lote 23 (#1586) que documentou a nova "classe
de risco 17" (tag single-anchor aninhada dentro do wrapper `inicio`/
`fim` de um par e descartada silenciosamente por
`_text_element_to_labels`). Essa mesma classe de risco e exatamente o
que a PR concorrente #1588 (ver leitura de PRs) corrige em codigo --
uma vez mergeada, o workaround de reposicionamento de tag documentado
no backlog deixa de ser estritamente necessario, mas continua correto
e nao sera removido preventivamente nesta rodada (nenhuma evidencia
ainda de que #1588 esteja mesclada).

O relatorio `AgentRun` mais recente
(`knowledge/agent-runs/2026-09-19-exciting-mccarthy-gbf44b/run.md`)
fechou com `result_state: merged` (lote 22, PR #1585) e um `next_move`
que ja antecipava a necessidade de reescanear `data/segmenter_samples/*.jsonl`
ao vivo para o proximo tier de menor `store_count` -- o lote 23,
mesclado depois desse relatorio, ja avancou parte desse proximo passo
(TRF2 quase esgotado). Esta rodada reescaneia ao vivo, sem assumir que
a tier documentada em gbf44b ainda reflete o estado atual do store.

`knowledge/agent-runs/index.md` continua marcando o mecanismo `AgentRun`
como legado para o loop horario (substituido por Wisk), mas o prompt
agendado desta sessao especifica ainda instrui explicitamente o
scaffold `AgentRun` e `BacklogItem` nao esta na lista de tipos
descontinuados. Essa tensao ja foi escalada uma vez (to0ars,
2026-09-14) e reconfirmada sem fato novo por 7+ rodadas subsequentes
(zrek2s, 83kr8s, hv2ep2, imy2ed, 5lvbii, j2t668, epgxv2, gbf44b) --
nenhum fato novo nesta rodada justifica reabrir a escalada.
