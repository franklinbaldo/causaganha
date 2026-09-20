---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-fv62kx-decision-real-cleaner-not-html-unescape"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
question: "Um scan inicial simplificado (html.unescape() apenas) sugeriu TRF4 como tribunal viavel com 5 candidatos elegiveis para o proximo lote -- mas a classe de risco 16 ja documentada afirma que TRF4 esta inutilizavel (candidatos colapsam abaixo do piso apos limpeza HTML real). Confiar no scan simplificado ou reverificar com o limpador real antes de selecionar candidatos?"
choice: "Reverificar com o limpador HTML real do lote 3 (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py) antes de aplicar o piso de 2500 caracteres. Resultado: 0 candidatos TRF4 elegiveis, confirmando a classe de risco 16 e descartando o resultado do scan simplificado."
rationale: "knowledge/backlog/issue-1050.md documenta a classe de risco 16: candidatos TRF4 pareciam elegiveis pelo comprimento bruto mas colapsavam bem abaixo do piso apos a limpeza real (markup embutido removido). Um primeiro scan ad-hoc desta rodada, usando so html.unescape(), reportou incorretamente TRF4 com 5 candidatos elegiveis -- reaplicar o limpador real do lote 3 confirmou 0 elegiveis, reconfirmando a classe de risco 16 em vez de reintroduzi-la por engano."
---

# Decisão: usar o limpador HTML real (não html.unescape) na seleção de candidatos

Um scan inicial desta rodada, com uma versão simplificada usando apenas
`html.unescape()`, sugeriu TRF4 como viável (5 candidatos acima do piso
de 2500 caracteres). Isso contradiz diretamente a classe de risco 16
já documentada (TRF4 inutilizável até novo arquivo de amostra
aparecer). Antes de confiar nesse resultado e desperdiçar um lote
inteiro (como aconteceu no lote 18), reaplicamos o limpador HTML real
usado pelas rodadas anteriores
(`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`)
sobre o mesmo pool — o resultado corrigido mostrou 0 candidatos TRF4
elegíveis, confirmando que a classe de risco 16 continua válida e que
o scan simplificado teria sido uma fonte de erro real nesta rodada.
