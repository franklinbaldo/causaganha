---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-x3954c-decision-length-bound-not-embedding-or-sampling"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
question: "Como reduzir o custo O(n^2) de find_near_duplicates sem trocar a semantica de deteccao (SequenceMatcher/RFC 0012 Sec 10) por embeddings, amostragem ou um limite de tamanho de corpus?"
choice: "Podar candidatos usando dois limites superiores comprovaveis e sem falso-negativo: (1) limite matematico de comprimento (ratio() = 2*M/T com M <= min(len_a,len_b), entao um par so pode atingir o threshold se 2*min/soma >= threshold) para descartar pares inteiros antes de normalizar/instanciar SequenceMatcher; (2) quick_ratio() do proprio SequenceMatcher (limite superior garantido e barato) para descartar antes do ratio() completo. Nenhuma mudanca de algoritmo de similaridade, nenhuma dependencia nova, nenhum parametro de amostragem que arriscasse perder um near-duplicate real."
rationale: "RFC 0012 Sec 10 (referenciado em splits.py e dedup.py) especifica SequenceMatcher/edit-distance como o metodo de deteccao, deliberadamente 'stdlib only, no embedding model' -- introduzir embeddings mudaria a semantica de match (aproximacao vetorial em vez de similaridade de sequencia exata) e o comportamento de dedup ja sancionado, sem necessidade: os dois limites escolhidos sao provas matematicas, nao heuristicas -- garantidamente zero falsos negativos, ao contrario de amostragem ou de um corte arbitrario por tamanho de corpus (que trocaria um bug de desempenho por um bug de correcao, exatamente o tipo de erro que a licao do batch24 registrada em knowledge/backlog/issue-1050.md ja identificou como custoso)."
---

# Decisao: poda por limite comprovavel, nao troca de algoritmo

Duas alternativas descartadas antes de implementar:

1. **Amostragem/particionamento por tribunal ou lote.** Reduziria custo
   mas reintroduziria exatamente o bug que o batch24 documentou (dedup
   que so compara dentro do lote, nao contra o corpus inteiro, deixou
   passar um near-duplicate ja rejeitado). Rejeitada.
2. **Trocar SequenceMatcher por embeddings/hashing aproximado
   (MinHash, embeddings + cosseno).** Mudaria a semantica de deteccao
   documentada em RFC 0012 Sec 10 e no proprio docstring do modulo
   (`dedup.py`: "stdlib only, no embedding model"), exigiria nova
   dependencia, e teria que ser revalidada contra os oito allowlist
   entries de falso-positivo ja documentados nos testes de regressao.
   Rejeitada como fora de escopo para uma correcao de desempenho.

A escolha implementada (limite de comprimento + `quick_ratio()`) e
estritamente uma otimizacao do MESMO algoritmo, com garantia formal
(nao probabilistica) de que nenhum par que atingiria `threshold` pode
ser descartado -- validada por teste comparando contra uma
implementacao de referencia sem poda (`test_find_near_duplicates_matches_brute_force_across_thresholds_and_lengths`).
