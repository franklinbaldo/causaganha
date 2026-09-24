---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-x3954c-decision-preserve-insertion-order-for-asymmetric-ratio"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
question: "A primeira versao da poda ordenava candidatos por comprimento (necessario para o corte por janela), e passava (menor, maior) diretamente para SequenceMatcher(None, a, b). O teste de equivalencia com a implementacao de referencia falhou em threshold=0.5 com 4 pares a mais no resultado podado -- por que, e como corrigir sem perder o ganho de desempenho?"
choice: "SequenceMatcher(None, a, b).ratio() nao e garantidamente simetrico (a busca de blocos combinantes usa estatisticas de popularidade/junk construidas a partir de b). Corrigido preservando a ordem de insercao original do dict `records` apenas na hora de montar o par para o SequenceMatcher (id_a, id_b = ordem de insercao), mantendo a ordenacao por comprimento so para decidir QUAIS pares sao candidatos (a janela de poda), nao para decidir a ordem dos argumentos da comparacao real."
rationale: "Descoberto ao vivo pelo proprio teste de equivalencia (test_find_near_duplicates_matches_brute_force_across_thresholds_and_lengths), que comparou a saida podada contra uma implementacao de referencia O(n^2) sem poda em varios thresholds -- exatamente o proposito desse teste. Sem essa correcao, a poda teria introduzido uma mudanca de comportamento sutil e dependente de dados (pares poderiam cruzar o threshold de forma diferente dependendo de qual texto vira 'a' vs 'b'), quebrando a garantia central do goal (mesmo conjunto de pares reportado)."
---

# Decisao: preservar ordem de insercao para a comparacao real

A visita inicial a implementacao assumia (incorretamente) que
`SequenceMatcher(None, a, b).ratio() == SequenceMatcher(None, b,
a).ratio()` sempre -- o que e quase sempre verdade na pratica mas nao
e uma garantia da API do `difflib` (a heuristica `autojunk` e o
algoritmo de blocos combinantes usam `b` como referencia para as
estatisticas de popularidade). Ordenar por comprimento para fins de
poda (necessario para o corte por janela monotonica) trocava
silenciosamente qual texto era `a` e qual era `b` em relacao a ordem de
insercao original usada pela implementacao de referencia -- causando
divergencia real (nao so de ordem do tuplo de saida) em pelo menos 4
pares de um corpus sintetico de 18 documentos em threshold=0.5.

Corrigido separando as duas preocupacoes: `order` (ordenado por
comprimento) decide apenas quais pares entram na janela de candidatos;
um mapa `insertion_index` decide, para cada par candidato, qual dos
dois documentos e passado como primeiro argumento ao
`SequenceMatcher`, replicando exatamente o comportamento da
implementacao de referencia. Reconfirmado verde apos a correcao.
