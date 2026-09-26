---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-p08457-decision-simulate-before-annotating"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
question: "Dado que assign_splits recomputa a particao val/test inteira a partir de uma ordem de hash fixa (seed, group_id) a cada chamada -- e nao existe forma de escolher diretamente em qual split um documento especifico vai cair -- como escolher quais dos 141 candidatos elegiveis (anotacao unica, seeded_with=='none', sem review) adjudicar nesta rodada, dado o orcamento de tempo?"
choice: "Simular assign_splits com cada candidato adicionado isoladamente a evaluation_eligible (sem gastar esforco de anotacao) para descobrir quais realmente aumentam test_count, depois simular novamente os 2 candidatos escolhidos EM CONJUNTO (nao so isoladamente) antes de comecar a anotacao, e so entao escolher os 2 documentos mais curtos desse conjunto validado (2604 e 3468 caracteres) para caber no orcamento da rodada."
rationale: "A simulacao isolada (141 candidatos, um de cada vez) mostrou 134 aumentariam test_count -- a maioria do pool serve o objetivo, entao tratabilidade (tamanho do documento) e um criterio de desempate razoavel. Mas simulacao isolada nao garante o resultado conjunto: adicionar 2 candidatos ao mesmo tempo insere ambos na mesma ordem de hash fixa, podendo interagir de forma nao-aditiva. A simulacao conjunta (antes de qualquer anotacao) confirmou test_count 2->4 com os 2 documentos escolhidos -- mesmo que, curiosamente, os dois proprios documentos acabem alocados para val nessa simulacao (outros 2 documentos ja elegiveis sao deslocados para test) -- o que e o comportamento correto e esperado do algoritmo determinismico, nao um defeito: o contrato real desta rodada e o metric agregado (test_count), nao qual documento especifico cai em qual split."
---

# Decisao: simular assign_splits antes de gastar esforco de anotacao

`assign_splits` recomputa a particao inteira a cada chamada a partir de
uma ordem de hash fixa -- nao da para escolher por identidade em qual
split um documento cai. Por isso, antes de anotar qualquer documento,
simulamos `assign_splits` com cada candidato (isolado, depois em
conjunto) adicionado a `evaluation_eligible`, e so entao escolhemos os
2 documentos mais curtos do conjunto confirmado a aumentar
`test_count` de 2 para 4.
