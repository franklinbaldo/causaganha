---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-advanced-routes-nav-parity"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "diff"
reference: "web/src/layouts/Layout.astro (both versions); web/src/components/SiteNav.astro (main, deleted by this PR); web/src/components/CommandPalette.astro (main, deleted by this PR); web/src/components/LawyerCard.astro (reboot/cobogo-web head)"
summary: "Old SiteNav.astro defined a two-tier nav: primary=[Processo, Publicações], secondary (behind a 'Mais' <details>)=[Minhas consultas, Cobertura/stats, Agentes, Projeto & dados/sobre]. New Layout.astro keeps the same two-tier shape: primary=[Processo, Publicações, Salvos/minhas-consultas], 'Mais' dropdown=[Cobertura, Agentes, Projeto & dados, GitHub]. Neither the old SiteNav.astro nor the old CommandPalette.astro (both read at main d2a4530) ever linked to /explorador or /changelog — those routes were already reachable only by direct URL or cross-links (e.g. LawyerCard.astro linking to /advogados/{tribunal}) before this PR, not something this PR newly hid. Satisfies point 6 of the owner's review request: advanced routes remain findable at the same level of discoverability as before, with no new competition against Processo/Publicações."
---

# Evidência — hierarquia de navegação (avançado vs. primário) preservada

O novo `Layout.astro` reproduz a mesma estrutura de dois níveis do `SiteNav.astro` antigo; `/explorador` e `/changelog` já não estavam no nav em nenhuma das duas versões — não é regressão desta PR.
