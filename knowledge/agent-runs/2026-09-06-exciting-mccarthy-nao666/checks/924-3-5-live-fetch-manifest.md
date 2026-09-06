---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-nao666-check-924-3-5-live-fetch-manifest"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
command: "curl -sSL https://archive.org/download/causaganha-dashboard/consolidation-manifest.json | python3 -c \"import json,sys; m=json.load(sys.stdin); items=m['items']; from collections import Counter; print(len(items), Counter(i.get('layout_revision','') for i in items))\""
result: "observed"
evidence_id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-3-5-consolidation-manifest-live"
summary: "HTTP 200, 43212 bytes. 23 items total, all 23 with layout_revision=\"\" (none yet at CURRENT_LAYOUT_REVISION=\"1\"). Confirms the mechanism (PR #785) is correct and the real backlog is the entire tracked archive, expected given A1's production benchmark hasn't run."
---

# Check — fetch ao vivo do consolidation-manifest.json real (IA)

Corrige a tentativa de rodada anterior que buscou em GitHub Pages e recebeu 404; o caminho real é o item IA `causaganha-dashboard`.
