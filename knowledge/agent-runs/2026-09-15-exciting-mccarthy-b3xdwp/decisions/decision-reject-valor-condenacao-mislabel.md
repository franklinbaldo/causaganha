---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-b3xdwp-decision-reject-valor-condenacao-mislabel"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
question: "A anotação histórica (família prompt_subagents:haiku) de doc_6b714f6515beb1d38ba465e57c60c669 marcou 'R$ 8.136,00' como valor_condenacao. O subagente independente desta rodada (general-purpose) não marcou nada nessa posição. O span está correto?"
choice: "Rejeitado o valor_condenacao de A. O texto onde o span aparece é o campo de cabeçalho do processo ('Valor da ação: R$ 8.136,00'), não um valor de condenação, e o dispositivo desta sentença é JULGO IMPROCEDENTE -- o pedido do autor (Nilton Nogueira de Souza) foi negado, então não há condenação monetária de ninguém a favor de ninguém neste documento. Nenhum valor_condenacao foi incluído na resolução final."
rationale: "A guideline define valor_condenacao como 'Monetary amount in a condemnation'. O 'Valor da ação' é o valor atribuído à causa para fins processuais (cálculo de custas, competência), uma convenção processual distinta e sempre presente no cabeçalho de qualquer petição, não uma consequência do julgamento. Como o resultado desta sentença é a improcedência total do pedido do autor, não existe nenhuma condenação em dinheiro a apurar -- só custas/honorários (categoria distinta, tageada corretamente por A como honorarios_inicio/fim). Esta não é uma discordância de fronteira de span (as duas anotações concordam em não ter valor_condenacao em nenhum outro lugar do documento); é um erro de categoria da anotação histórica, capturado só porque a adjudicação desta rodada comparou o texto do span contra o resultado operativo real do documento em vez de aceitar a categoria pelo rótulo."
---

# Decisão: rejeitar `valor_condenacao` mal rotulado em doc_6b714f65

A anotação histórica confundiu "Valor da ação" (campo processual de
cabeçalho, presente em toda petição/sentença) com "valor de condenação"
(quantia que o dispositivo efetivamente manda pagar). Como o dispositivo
desta sentença é `JULGO IMPROCEDENTE`, não há condenação monetária real no
documento -- o span foi descartado na resolução final, em vez de mantido
por "vir da anotação histórica".
