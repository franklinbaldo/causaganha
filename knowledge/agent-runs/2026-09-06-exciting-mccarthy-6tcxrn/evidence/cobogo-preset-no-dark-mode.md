---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-6tcxrn-evidence-cobogo-preset-no-dark-mode"
run_id: "2026-09-06-exciting-mccarthy-6tcxrn"
goal_id: "2026-09-06-exciting-mccarthy-6tcxrn-goal-1178-single-theme-decision"
kind: "other"
reference: "web/node_modules/cobogo/preset/index.mjs (installed live via `npm ci` in web/, package github:franklinbaldo/cobogo#8ad1fe1) and web/node_modules/cobogo/skills/cobogo/SKILL.md"
summary: "grep -in 'theme|tema|light|dark|condition|semanticTokens' against the installed preset shows exactly one semanticTokens.colors block (canvas/surface/surfaceMuted/text/textMuted/border/accent/accentText/info/attention — all single flat values, e.g. canvas -> {colors.paper}) and zero Panda `conditions` entries; the only two 'dark' hits are unrelated recipe visual-variant names (button/card tone='dark', a literal high-contrast style choice, not a color-mode switch) at lines 172 and 193. The preset has no data-theme concept whatsoever. The bundled SKILL.md explicitly instructs consumers to prefer an existing Cobogó token/recipe over a project-local visual equivalent, and to improve the shared preset instead when a decision would generalize — ruling out a project-local dark-mode shim as the correct fix here."
---

# Evidência — o preset Cobogó não tem modo escuro

Instalação real do pacote (`npm ci` em `web/`) e leitura de `node_modules/cobogo/preset/index.mjs` confirmam: um único palette de cores semânticas, sem `conditions` do Panda, sem qualquer noção de `data-theme`. As duas ocorrências de "dark" no arquivo são variantes de recipe (botão/card), não um mecanismo de tema.
