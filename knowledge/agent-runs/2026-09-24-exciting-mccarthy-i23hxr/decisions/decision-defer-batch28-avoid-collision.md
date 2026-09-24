---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-i23hxr-decision-defer-batch28-avoid-collision"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
question: "document_count=193 e val/test ceiling ainda 29/29 (< piso RFC 0012 Sec5 item4 de >=30/>=30) -- o proximo passo padrao das ~27 rodadas anteriores seria selecionar e ingerir um vigesimo oitavo lote real. Esta rodada deve fazer isso agora?"
choice: "Nao. #1605 (batch27, aberta por outra sessao ha ~25min, mergeable_state=clean, CI ainda pending) ja cobre o proximo lote natural desta linhagem. Adiar batch28 para depois de #1605 mesclar e selecionar outro trabalho real desta rodada (goal-repair-audit-blind-spot)."
rationale: "Ingerir um batch28 antes de #1605 mesclar arriscaria exatamente a classe de erro ja documentada na licao do batch14: colisao de near-duplicate/document_id entre lotes concorrentes que nao se veem um ao outro ate o merge. Nao ha necessidade de correr esse risco quando existe trabalho real, independente e imediatamente acionavel (o ponto cego de teste em segmenter_semantic_audit.py) que nao depende de #1605 mesclar primeiro."
---

# Decisao: adiar o vigesimo oitavo lote de #1050

Trabalho de dominio real foi feito nesta rodada, mas nao na forma de
mais um lote de ingestao -- ver `goal_ids` para o que foi selecionado
em seu lugar.
