---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-230b86-evidence-issue-1652-opened"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-catalog-discovery-allowlist"
kind: "issue"
reference: "https://github.com/franklinbaldo/causaganha/issues/1652"
summary: "Issue nova aberta consolidando a classe de ameaca 'IA discovery must never trust an unauthenticated global search as canonical' com secao 'status por superficie' cobrindo (1) scripts/generate_catalog.py -- fechado nesta rodada, (2) scripts/reconcile_processos.py::_discover_juris_items (JURIS fallback) -- aberto, diagnostico existente em PR externa #1644 stale/lint-failing, (3) scripts/reconcile_processos.py autenticacao por digest -- aberto, diagnostico existente em PR externa #1645 stale/CodeQL+tests-failing. docs/SECURITY_THREAT_MODEL.md ganhou a linha TM-16 referenciando esta issue, e a secao 5 (Ordem de execucao) foi atualizada com o item 10."
---

# Evidência: issue #1652 + TM-16

Nova issue e nova linha de matriz dão rastreamento formal a uma classe de
ameaça que ficava apenas implícita em três PRs externas, sem nenhuma linha
correspondente na matriz de segurança.
