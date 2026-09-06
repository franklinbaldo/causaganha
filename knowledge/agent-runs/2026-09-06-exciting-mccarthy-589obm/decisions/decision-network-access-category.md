---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-589obm-decision-network-access-category"
run_id: "2026-09-06-exciting-mccarthy-589obm"
goal_id: "2026-09-06-exciting-mccarthy-589obm-goal-fix-backlog-985-category"
question: "#985's real blocker is that this session's runtime cannot fetch TSE's official ZIPs (Akamai returns 403 Access Denied network-wide, previously DNS failed outright). Should this be recorded under the existing 'credentials' category, under 'infra_decision', or as a new BacklogItem category?"
choice: "Add a new category value, 'network_access', to BacklogItem's CHECK constraint in knowledge/okf.schema.sql and to tests/knowledge/test_backlog.py's VALID_CATEGORIES, and file #985 under it."
rationale: "'credentials' means auth material (a key/token) is absent from the environment — #985 has no such gap; a correctly-authenticated request would still be rejected, because the block operates on the request's network origin, not its credentials. 'infra_decision' means a human must choose a hosting/design option before code can proceed — #985 needs no such choice; the acquisition code (src/tse_processual/acquisition.py) is already written, reviewed, and merged, and would work immediately from a runtime whose egress isn't blocked. Neither existing category names the actual condition: an otherwise-correct request is rejected because of where it originates. This is also not a one-off: any future live-fetch step against a Brazilian government CDN (DataJud, other TSE/TCU endpoints) is likely to hit the same wall, so a named category makes it discoverable and greppable across the backlog rather than re-describing the same network condition in free text each time under a mismatched category. This is well within this round's explicit authorization to extend OKF types/schemas when the existing model is a poor fit for the work being represented."
---

# Decisão: nova categoria `network_access` no BacklogItem

`credentials` (falta credencial) e `infra_decision` (falta decisão humana) não descrevem o bloqueio real da #985: a requisição seria idêntica com ou sem credenciais/decisão — ela é rejeitada pela origem de rede (Akamai devolve 403 "Access Denied" em todo `tse.jus.br`, hoje sem sequer falha de DNS como em rodadas anteriores). Criei a categoria `network_access` no schema e no teste, por ser um padrão recorrente (qualquer fonte governamental brasileira atrás de WAF/CDN pode repetir esse bloqueio) que merece nome próprio em vez de texto livre sob uma categoria errada.
