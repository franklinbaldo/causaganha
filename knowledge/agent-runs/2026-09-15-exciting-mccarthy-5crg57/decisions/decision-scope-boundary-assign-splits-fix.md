---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-5crg57-decision-scope-boundary-assign-splits-fix"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
question: "Com 2 documentos evaluation-eligible reais produzidos nesta rodada, `python -m segmenter_dataset assign-splits` ainda recusa produzir um manifest completo (ambos os documentos caem no mesmo papel, val ou test fica vazio) -- uma limitação pré-existente e já documentada do algoritmo (RFC 0012 §10, achado de review do PR #838: sem fallback para grupo menor quando um grupo elegível excede o tamanho-alvo restante). Esta rodada deve tentar corrigir o algoritmo de splits.py para que o CLI completo funcione já com uma amostra tão pequena?"
choice: "Não. O sinal de sucesso do goal desta rodada (evaluation_eligible_count>=1, medido por scripts/segmenter_governance_status.py) já foi alcançado e verificado ao vivo contra a store real -- review_count 0->2, evaluation_eligible_count 0->2. Registrar o achado do CLI como evidência honesta (evidence-second-real-review) e deixar a correção do algoritmo, se necessária, para quando o volume real de documentos adjudicados crescer o suficiente para o problema realmente importar (RFC 0012 §5.4: >=30 val + >=30 test)."
rationale: "Mudar o algoritmo de assign_splits (splits.py) para funcionar com uma amostra de 2 documentos seria otimizar para um caso de teste artificialmente pequeno, não para o uso real do pipeline -- com as metas do §5.4 (>=30 val, >=30 test), o problema de 'grupo elegível excede o tamanho-alvo restante' deixa de ocorrer estruturalmente. Investir esforço agora em um fallback de grupo menor arriscaria uma mudança de algoritmo não testada contra o caso real que o RFC pede, além de estar fora do escopo do goal desta rodada (produzir o primeiro/segundo ReviewRecord real, não reformar o splitter). O achado fica registrado como evidência real e específica para orientar rodadas futuras que escalarem o volume de documentos adjudicados."
---

# Decisão: não perseguir uma correção do splitter nesta rodada

O goal desta rodada era produzir o primeiro ReviewRecord real da store -- alcançado e verificado (evaluation_eligible_count 0->2). A limitação do CLI completo de `assign-splits` com apenas 2 documentos é um achado real, mas resolvê-la corretamente exige volume real (RFC 0012 §5.4), não um ajuste ad hoc para uma amostra de teste. Registrado como escopo para rodada futura de escala, não como bloqueio desta.
