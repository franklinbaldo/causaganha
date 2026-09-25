---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-230b86-decision-defer-1644-1645-new-issue"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-catalog-discovery-allowlist"
question: "As PRs externas #1644 (lint falhando) e #1645 (CodeQL + tests (tjro) falhando) devem ser adotadas/reescritas nesta rodada junto com #1643, ou deixadas para uma rodada futura?"
choice: "Nao adotar nem reescrever #1644/#1645 nesta rodada. Abrir issue nova (#1652) consolidando as tres superficies da mesma classe de ameaca (generate_catalog.py, ja fechado nesta rodada; reconcile_processos.py JURIS fallback; reconcile_processos.py autenticacao por digest), com secao 'status por superficie' explicita, e adicionar TM-16 a matriz. Registrar #1644/#1645 como pendentes de rebase + retrabalho, nao como 'nao investigadas'."
rationale: "#1644 tem o check 'lint' com conclusion=failure e #1645 tem 'CodeQL' e 'tests (tjro)' com conclusion=failure -- diferente de #1643 (diff minimo, CI totalmente verde), essas duas tem falhas genuinas que precisam de diagnostico e possivelmente redesenho (nao apenas rebase), alem de tocarem reconcile_processos.py, um modulo maior e com mais superficie de teste do que generate_catalog.py. Tentar absorver as tres numa unica rodada arriscaria entregar uma fatia mal verificada sob pressao de tempo. O ganho real desta rodada nao e fechar as tres imediatamente, e sim parar o ciclo de 'sinalizado como nao investigado' repetindo-se rodada apos rodada sem nunca virar um veredito -- isso foi alcancado ao dar a essa classe de ameaca um lugar formal (issue + linha de matriz) com status concreto por superficie, para que uma rodada futura com foco dedicado em reconcile_processos.py possa retomar de um ponto de partida claro em vez de rederivar o diagnostico do zero."
---

# Decisão: não adotar #1644/#1645 nesta rodada

Diferente de `#1643`, essas duas PRs têm CI genuinamente vermelho sobre um
módulo maior (`reconcile_processos.py`). Absorvê-las nesta rodada arriscaria
uma entrega mal verificada. Em vez disso, esta rodada encerra o ciclo de
"não investigado" registrando um veredito concreto (issue `#1652` + `TM-16`
com status por superfície), deixando um ponto de partida claro para a
próxima rodada que focar em `reconcile_processos.py`.
