---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ttdopu-evidence-claude-md-diff"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal_id: "2026-09-06-exciting-mccarthy-ttdopu-goal-fix-css-token-boundary-docs"
kind: "diff"
reference: "git diff CLAUDE.md (### CSS token boundary section)"
summary: "Replaced the retired 'two token systems split by page type (Brazilian Modernism vs. Semantic, including --pico-*/--tinta-*)' description with one grounded in live grep evidence: a single Panda CSS design system via the `cobogo` preset covering all substantive pages, with `web/src/index.css` documented as a compatibility-alias bridge consumed only by four named, not-yet-converted Svelte islands. Also states forward guidance (new work uses Panda; the four named components may keep using their existing legacy names; don't reintroduce a page-type boundary)."
---

# Evidência: diff da fronteira CSS em CLAUDE.md

Substituição da seção obsoleta por uma descrição verificada ao vivo (grep em `web/src`, leitura de `web/panda.config.ts`, `web/src/index.css`, `web/src/styles/query-states.css` e das quatro páginas .astro não migradas identificadas).
