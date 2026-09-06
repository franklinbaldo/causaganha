---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-theme-toggle-orphaned-regression"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "diff"
reference: "web/src/components/PageHeader.astro:2,49 (deleted by this PR, main d2a4530); web/src/components/ThemeToggle.astro (untouched, still present on reboot/cobogo-web head); web/src/layouts/Layout.astro pre-paint script (deleted by this PR); web/src/index.css (reboot/cobogo-web head)"
summary: "git grep -n ThemeToggle on main (d2a4530) shows PageHeader.astro:2 importing it and PageHeader.astro:49 rendering <ThemeToggle /> — the only consumer in the whole tree besides the component's own definition. This PR deletes PageHeader.astro (confirmed in the diff stat: 52 lines removed, 0 added) but does not delete web/src/components/ThemeToggle.astro, which remains in the tree on the PR head with zero references anywhere (git grep -n ThemeToggle on the PR head returns only ThemeToggle.astro itself). The PR also deletes Layout.astro's pre-paint inline script that used to set document.documentElement.setAttribute('data-theme', ...) from localStorage/prefers-color-scheme before first paint. ThemeToggle.astro's own <style> block references --color-base-200, --font-size-sm, --radius-btn, and --transition-base; grepping the new web/src/index.css and web/panda.config.ts for these four strings returns zero matches, confirming the component would render with missing variables even if re-wired. No test (on main or on this PR head) exercises theme toggling. Net effect: dark/light theme switching, previously available on every page via PageHeader, is silently absent from the entire rebooted site, and the PR leaves behind a dead component referencing tokens that no longer exist — a real, unflagged regression under the PR's own stated goal of a clean CSS/legacy purge (point 5 of the owner's review request)."
---

# Evidência — `ThemeToggle.astro` órfão + dark mode removido silenciosamente

`PageHeader.astro` (único lugar que renderizava `ThemeToggle`) foi apagado, mas `ThemeToggle.astro` não — ficou morto, referenciando variáveis CSS inexistentes na nova base, e nenhuma página tem mais alternância de tema.
