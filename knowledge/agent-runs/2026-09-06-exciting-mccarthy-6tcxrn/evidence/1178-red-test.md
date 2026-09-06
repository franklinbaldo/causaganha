---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-6tcxrn-evidence-1178-red-test"
run_id: "2026-09-06-exciting-mccarthy-6tcxrn"
goal_id: "2026-09-06-exciting-mccarthy-6tcxrn-goal-1178-single-theme-decision"
kind: "test_red"
reference: "web/src/lib/themeSingleModeGuard.test.ts, first run against unmodified tree (ThemeToggle.astro still present)"
summary: "`npx vitest run src/lib/themeSingleModeGuard.test.ts` fails both assertions before any removal: 'does not ship an orphaned ThemeToggle component' fails because existsSync(.../ThemeToggle.astro) is true, and 'has no source file referencing the removed light/dark theming plumbing' fails listing all 6 legacy markers (data-theme, causaganha-theme, --font-size-sm, --radius-btn, --transition-base, --color-base-200) found inside ThemeToggle.astro. This is the RED step of the TDD cycle for #1178: the test encodes the desired end-state (no orphaned theming code) before the fix is applied."
---

# Evidência — teste RED antes da remoção

`vitest run` no arquivo novo falha nas duas asserções contra a árvore original, listando exatamente os seis marcadores legados encontrados em `ThemeToggle.astro`.
