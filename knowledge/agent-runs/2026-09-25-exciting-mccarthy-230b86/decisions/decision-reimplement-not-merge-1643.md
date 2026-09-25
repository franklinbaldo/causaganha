---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-230b86-decision-reimplement-not-merge-1643"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-catalog-discovery-allowlist"
question: "A PR externa #1643 (codex, diff minimo e correto, CI 13/13 verde na sua propria sha) esta pronta para merge direto via API, ou o fix deve ser reimplementado nesta sessao?"
choice: "Reimplementar o fix desta sessao com TDD proprio (2 testes RED->GREEN em tests/test_archive_partitions.py, mesma extracao discover_catalog_items() em scripts/generate_catalog.py) em vez de tentar contornar o bloqueio de branch protection em #1643."
rationale: "A tentativa de merge_pull_request em #1643 falhou com 405 'Required status check GitGuardian Security Checks is expected' -- a branch protection nao reconhece os check runs ja completados naquela sha/contexto como satisfazendo o gate atual, provavelmente porque main avancou ~15 commits desde o base da PR (sha 7dc8094) e o mecanismo de check exigido esta atado a um contexto que precisaria de um push novo para ser recomputado. Contornar isso (forcar merge, ou pushar na branch codex/... que nao e desta sessao) violaria tanto a politica de nao pular gates quanto a convencao de nao pushar em branch alheia sem permissao explicita. Como nenhum arquivo tocado pela PR mudou em main desde o base dela, o fix e pequeno (54+/22-, 2 arquivos) e a logica ja foi verificada correta por leitura direta do codigo (confirmado que main() so chamava get_items_from_sync_manifest() dentro do branch 'not args.full and not args.verified_inventory', entao verified_inventory=True sempre caia no fallback list_ia_items()), reimplementar com testes proprios desta sessao e mais barato e mais seguro do que negociar o gate de branch protection, e produz verificacao fresca (RED confirmado nesta sessao, nao herdado)."
---

# Decisão: reimplementar em vez de mesclar #1643 diretamente

`merge_pull_request` em `#1643` falhou por um gate de branch protection
("GitGuardian Security Checks" não reconhecido nesse contexto), não por
um problema real no diff. Como o fix é pequeno, correto e não conflita
com nada que mudou em `main` desde o base da PR, reimplementá-lo com TDD
próprio nesta sessão é mais barato e mais seguro do que forçar o merge ou
pushar na branch de outra sessão/agente sem permissão.
