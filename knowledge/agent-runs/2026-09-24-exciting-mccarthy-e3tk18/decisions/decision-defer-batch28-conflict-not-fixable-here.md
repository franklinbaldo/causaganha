---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-e3tk18-decision-defer-batch28-conflict-not-fixable-here"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
question: "#1605 (batch27, branch alheia claude/exciting-mccarthy-034xwb) esta com mergeable_state='dirty' (conflito real, provavelmente com #1606 ja mesclado por cima da mesma base). Esta rodada deve resolver esse conflito, ou selecionar e ingerir um vigesimo oitavo lote proprio para #1050 em paralelo?"
choice: "Nenhum dos dois. Nao resolver o conflito de #1605 (exigiria editar arquivos numa branch de outra sessao, o que a politica desta sessao proibe sem permissao explicita -- diferente de uma chamada de sincronizacao de rotina como update_pull_request_branch, ja usada em rodadas anteriores para PRs so 'behind', nao 'dirty'). Nao selecionar um batch28 concorrente (repetiria a licao do batch14: colisao de near-duplicate/document_id entre lotes concorrentes que nao se veem ate o merge -- e especialmente arriscado agora que ja existe um conflito real confirmado entre duas linhagens tocando os mesmos arquivos de data/segmenter/annotations/). Selecionar em vez disso o trabalho explicitamente deixado pendente pela rodada anterior (fechar a lacuna de teste remanescente da auditoria semantica)."
rationale: "Editar a branch 034xwb sem permissao explicita violaria a politica de branch desta sessao. Selecionar um lote novo em paralelo a uma PR ja em conflito repetiria exatamente o risco de colisao ja documentado, com uma probabilidade ainda maior de conflito dado que #1605 ja demonstrou que duas linhagens concorrentes de #1050 podem tocar os mesmos arquivos no mesmo dia. O trabalho de fechar o ponto cego de teste remanescente e real, independente, e nao tem nenhuma dessas dependencias -- e o proprio next_move da rodada anterior ja apontava para ele."
---

# Decisao: nao tocar #1605, nao iniciar batch28

Trabalho de dominio real foi feito nesta rodada, mas nao na forma de
mais um lote de ingestao nem de resolucao de um conflito de merge
alheio -- ver `goal_ids` para o que foi selecionado em seu lugar.
