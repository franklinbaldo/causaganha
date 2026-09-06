---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-layout-seo-static-preserved"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "diff"
reference: "web/astro.config.mjs:9; web/src/layouts/Layout.astro (reboot/cobogo-web head)"
summary: "web/astro.config.mjs:9 keeps `output: 'static'` unchanged by this PR (identical in main and the PR head). The rewritten Layout.astro still emits <link rel=\"canonical\">, the full og:*/twitter:* meta block, and <a href=\"#main-content\" class=\"skip-link\">Ir para o conteúdo principal</a>. Satisfies point 4 of the owner's review request."
---

# Evidência — SSG, canonical/OG e skip-link preservados

`output: 'static'` inalterado; `Layout.astro` novo mantém canonical, Open Graph/Twitter meta e skip-link.
