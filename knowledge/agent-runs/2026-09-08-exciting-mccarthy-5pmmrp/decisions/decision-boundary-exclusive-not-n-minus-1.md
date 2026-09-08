---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-5pmmrp-decision-boundary-exclusive-not-n-minus-1"
run_id: "2026-09-08-exciting-mccarthy-5pmmrp"
goal_id: "2026-09-08-exciting-mccarthy-5pmmrp-goal-fix-window-off-by-one"
question: "Fix the 'last N days' window by changing the WHERE clause's comparison operator (`>=` -> `>` against the unchanged `INTERVAL N DAY`), or by subtracting N-1 days instead?"
choice: "Change `date >= CURRENT_DATE - INTERVAL N DAY` to `date > CURRENT_DATE - INTERVAL N DAY`, keeping N (30, 120) unchanged."
rationale: "Both forms produce the same set of dates (today-(N-1)..today, N distinct dates), but `>` against the unchanged `INTERVAL N DAY` keeps the frontmatter's own stated window size (30, 120) as the single visible number in the SQL, matching the description strings ('last 30 days', 'last 120 days') and the UI label ('Últimos 30 dias') without introducing a second, easy-to-desync N-1 literal. This mirrors how the same class of bug reads most naturally to a future reader: the interval names the window's calendar span exactly, and the comparison decides inclusive-vs-exclusive at the boundary -- one number, one place to look."
---

# Decisão: corrigir com `>` no limite, não com N-1

Optei por trocar `>=` por `>` mantendo o `INTERVAL N DAY` original, em vez de mudar o número do intervalo para N-1. Isso preserva a correspondência 1:1 entre o número no SQL e o número no frontmatter/rótulo da UI ("30", "120"), evitando um segundo lugar onde o tamanho da janela poderia dessincronizar.
