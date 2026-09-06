---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-ucw90y-check-layout-static-og-skiplink-grep"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
command: "git show d2a4530:web/astro.config.mjs | grep -n output; git show origin/reboot/cobogo-web:web/astro.config.mjs | grep -n output; git diff d2a4530..origin/reboot/cobogo-web -- web/src/layouts/Layout.astro"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-layout-seo-static-preserved"
summary: "Both versions show `output: 'static'` at astro.config.mjs:9 (unchanged). The Layout.astro diff shows canonical link, full OG/Twitter meta block, and the skip-link anchor all still present in the rewritten file."
---

# Check — `output: static`, canonical/OG e skip-link confirmados
