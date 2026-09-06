---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-1na8o6-decision-explicit-ack-button"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
goal_id: "2026-09-06-exciting-mccarthy-1na8o6-goal-ack-pending-change"
question: "#1232 offers two acceptable acknowledgement gestures: an explicit small action ('Marcar como visto' / 'Atualizar referência'), or — 'se ficar mais simples e coerente' — treating opening the dossiê (the existing 'Abrir dossiê' link) as the acknowledgement. Which one to build?"
choice: "Add an explicit 'Marcar como visto' button, visible only while a change is pending, rather than overloading the existing 'Abrir dossiê' link with acknowledgement semantics."
rationale: "'Abrir dossiê' is a plain external navigation <a href> to a different page; making it also silently mutate localStorage baseline state on click would be a surprising side effect on a link that looks like read-only navigation, and is much harder to test deterministically (a full page navigation, not a click handler, is the real trigger) or to keyboard-verify independently of the navigation itself. An explicit button keeps 'read' and 'acknowledge' as two clearly separate, independently discoverable actions — matching the issue's own acceptance criterion 'existe uma ação clara para reconhecer a nova referência' — and reuses the exact `outline secondary` button pattern the component already uses for Renomear/Remover, so it introduces no new visual language and stays inside the CSS token boundary for this legacy Svelte island (CLAUDE.md: reuse existing --papel-*/--s-* names, don't invent new ones)."
---

# Decisão: botão explícito "Marcar como visto", não sobrecarregar "Abrir dossiê"

Um botão dedicado, visível só enquanto a mudança está pendente, mantém "ler" e "reconhecer" como dois gestos claramente separados e testáveis, e reaproveita a classe `outline secondary` já usada por Renomear/Remover — sem introduzir nova linguagem visual nem nova custom property CSS.
