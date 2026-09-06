---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-ucw90y-check-nav-parity-grep"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
command: "git show d2a4530:web/src/components/SiteNav.astro | head -80; git grep -n 'explorador\\|changelog\\|advogados' origin/reboot/cobogo-web -- 'web/src/**/*.astro' 'web/src/**/*.svelte' | grep -v 'pages/explorador.astro\\|pages/changelog.astro\\|pages/advogados'"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-advanced-routes-nav-parity"
summary: "Old SiteNav.astro's own primary/secondary link lists never included /explorador or /changelog; the only cross-link to an advanced route found in the new tree is LawyerCard.astro -> /advogados/{tribunal}, matching the pre-existing pattern. Confirms no new hiding of advanced routes was introduced by this PR."
---

# Check — paridade de navegação para rotas avançadas confirmada
