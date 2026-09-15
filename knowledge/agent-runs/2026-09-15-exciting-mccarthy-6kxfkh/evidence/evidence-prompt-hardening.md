---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6kxfkh-evidence-prompt-hardening"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
goal_id: "2026-09-15-exciting-mccarthy-6kxfkh-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter_splits/technique1_annotation_prompt.md"
summary: "Adicionado um piso numerico explicito ('menos de 8 tags para um documento >3000 chars e quase certamente errado, refaca') na etapa 5 de auto-verificacao do prompt canonico Tecnica 1, endereçando o achado de processo que pxa8pi registrou (subagentes ainda produzem rascunhos de 1 tag mesmo com o checkpoint existente de contagem de categorias). Os dois subagentes desta rodada, usando o prompt ja endurecido, produziram anotacoes completas (15 e 13 tags) na primeira tentativa -- comportamento observado consistente com a correcao, embora uma amostra de 2 nao seja prova estatistica."
---

# Evidencia: endurecimento do prompt canonico Tecnica 1

Diff (resumo): adicionado um bullet antes do existente "Does every category
from your step 3 list actually appear as a tag?", com um piso absoluto de
contagem de tags por tamanho de documento, e uma frase explicando por que
o piso existe (rascunhos de 1-2 tags ja passaram por todo o resto do
checklist).

Comportamento observado nesta rodada (n=2, nao e prova estatistica mas e o
unico dado disponivel): subagente A (general-purpose/sonnet,
doc_3cffd7961e9fc910f6ae628f5aaa6c40, acordao) produziu 13 tags brutos na
primeira tentativa; subagente B (general-purpose/haiku,
doc_888fe4545b72af4a84e0baa6a766dab4, sentenca) produziu 15 tags brutos na
primeira tentativa. Nenhum precisou de redirecionamento -- ao contrario da
rodada pxa8pi, onde um dos dois subagentes produziu inicialmente so 1 tag e
precisou ser redirecionado manualmente.
