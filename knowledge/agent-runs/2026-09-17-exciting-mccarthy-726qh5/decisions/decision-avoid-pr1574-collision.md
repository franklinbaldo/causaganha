---
type: AgentDecision
id: "2026-09-17-exciting-mccarthy-726qh5-decision-avoid-pr1574-collision"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
decision: "Continuar a linhagem #1050 com um decimo oitavo lote, mas excluir explicitamente os 6 document_id listados no corpo de PR #1574 (5 ingeridos + 1 descartado por quase-duplicata) da selecao de candidatos, em vez de esperar essa PR concorrente mesclar ou de trabalhar em outra issue."
rationale: "Todas as outras 20 issues abertas estao bloqueadas por credenciais/decisoes externas ausentes neste ambiente (confirmado ao vivo nas leituras desta rodada); #1050 e a unica issue com caminho de execucao provado e sem bloqueio. Esperar passivamente PR #1574 mesclar desperdicaria a rodada; abrir uma PR concorrente sem cuidado repetiria as colisoes ja documentadas (classes de risco 9/12 em issue-1050.md). Como o corpo de #1574 ja lista seus 6 document_id explicitamente, e possivel reduzir o risco de colisao a quase zero sem precisar esperar o merge: um scan ao vivo do pool (>200 candidatos elegiveis) tem probabilidade desprezivel de escolher exatamente os mesmos 6 IDs por acaso, e a exclusao explicita elimina esse caso remanescente."
---

# Decisao: evitar colisao com PR #1574 sem bloquear a rodada

`data/segmenter_samples/*.jsonl` tem mais de 200 candidatos elegiveis
e nunca usados (confirmado pela rodada anterior, epgxv2). PR #1574
consumiu exatamente 6 IDs conhecidos (listados no seu corpo). Em vez
de tratar a existencia de uma PR concorrente como bloqueio total desta
rodada, a estrategia adotada e: reescanear o pool ao vivo, remover os
6 IDs de #1574 da lista de candidatos elegiveis antes de escolher,
e prosseguir com o mesmo mecanismo ja provado por 17 lotes anteriores
(`scripts/ingest_djen_sample_technique1_batch.py`). Isso preserva
continuidade real de entrega nesta rodada sem exigir coordenacao
sincrona com a outra sessao nem arriscar reintroduzir as classes de
risco 9/12 (candidato ja ingerido por sessao concorrente).
