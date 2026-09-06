---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-buxwff-decision-text-link-not-button"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
goal_id: "2026-09-06-exciting-mccarthy-buxwff-goal-agents-home-discovery"
question: "How should the home hero's new /agentes CTA be styled, given the hero section has a dark background ('text' token) and #1219 explicitly warns against 'enfraquecer a clareza das duas entradas humanas se a terceira superfície for apresentada como um terceiro tipo de busca equivalente'?"
choice: "A plain underlined text link ('Usar com um agente →') appended to the hero's existing explanatory paragraph, not a third button in the CTA row. Confirmed in a real Chromium screenshot that this renders as light, legible text/underline against the dark hero background, clearly subordinate in visual weight to the two button()-styled CTAs."
rationale: "First tried button({ visual: 'outline' }) for the third CTA; a real browser screenshot revealed it was invisible — cobogo's button recipe defines outline as { background: transparent, color: 'text' }, i.e. dark text with no explicit border color override, which disappears against the hero's own 'text'-colored (dark) background. The only visible alternative recipe variant on a dark background is 'light' ({ color: 'canvas', borderColor: 'canvas' }), already used for the Publicações button — reusing it for Agentes would make the third entry look like an equally-weighted third search option, which is exactly the risk #1219 names. A subordinate text link resolves both problems at once: it is visible (light-colored inline text/underline, verified by screenshot) and it is visually secondary to the two solid/light buttons, keeping Processo/Publicações as the primary human entries per the issue's own acceptance criterion."
---

# Decisão: link de texto, não terceiro botão, para o CTA de agentes na home

Substituí `button({ visual: 'outline' })` (invisível sobre o hero escuro, confirmado por screenshot real) por um link de texto sublinhado dentro do parágrafo explicativo já existente. Isso evita tanto o bug de contraste quanto o risco que a própria #1219 nomeia: um terceiro botão do mesmo peso visual das duas entradas humanas principais.
