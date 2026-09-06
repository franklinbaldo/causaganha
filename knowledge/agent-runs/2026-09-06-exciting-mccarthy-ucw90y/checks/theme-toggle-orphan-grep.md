---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-ucw90y-check-theme-toggle-orphan-grep"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
command: "git grep -n ThemeToggle d2a4530 -- web/src; git grep -n ThemeToggle origin/reboot/cobogo-web -- web/src; git log d2a4530..origin/reboot/cobogo-web --oneline -- web/src/components/ThemeToggle.astro; git grep -c 'color-base-200\\|font-size-sm\\|radius-btn\\|transition-base' origin/reboot/cobogo-web -- web/src/index.css web/panda.config.ts"
result: "failed"
evidence_id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-theme-toggle-orphaned-regression"
summary: "On main, ThemeToggle is referenced only by PageHeader.astro (its sole consumer). On the PR head, the only match is ThemeToggle.astro's own definition — its consumer was deleted but it was not. No commit in the PR range touches ThemeToggle.astro itself (confirming it's leftover, not intentionally kept). The four CSS custom properties its <style> block depends on have zero occurrences in the new index.css/panda.config.ts. Marked 'failed' because this check surfaces a real defect in the PR under review, not a defect in this round's own work."
---

# Check — `ThemeToggle.astro` confirmado órfão, com variáveis CSS inexistentes

Resultado do check é a própria evidência da regressão: o consumidor foi apagado, o componente não, e as variáveis CSS que ele usa não existem mais.
