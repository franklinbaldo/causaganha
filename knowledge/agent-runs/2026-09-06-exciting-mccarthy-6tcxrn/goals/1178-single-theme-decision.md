---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-6tcxrn-goal-1178-single-theme-decision"
run_id: "2026-09-06-exciting-mccarthy-6tcxrn"
goal: "Resolve issue #1178 (orphaned ThemeToggle.astro after the Cobogó/Panda reboot) by determining, with live evidence, whether the current design-system foundation can support light/dark theming cleanly — then either restore a properly wired toggle on Cobogó/Panda tokens, or formally decide single-theme and remove the dead component plus a regression test guarding against it silently reappearing."
rationale: "#1178 is the repository owner's own immediate, explicit, 'READY para IMPLEMENTAÇÃO. Prioridade 1 pós-reboot' follow-up to a finding this session's own prior round (#1177) surfaced: the reboot deleted PageHeader.astro (the only renderer of ThemeToggle.astro) and the theme pre-paint script, but left ThemeToggle.astro itself in the tree referencing CSS custom properties that no longer exist anywhere in the new foundation — a real, silent feature loss with no test catching it. It is more directly actionable than any other open issue this round: it has concrete acceptance criteria, both valid outcomes are pre-authorized by the issue text, and per this round's OKF reading, the previous round's next_move explicitly named resolving the post-reboot web direction as the gate for exactly this kind of work."
success_signal: "A test exists that fails (RED) while the orphaned component and its dead CSS-variable references are present, and passes (GREEN) once the chosen resolution (restore-with-Cobogó-tokens or remove-as-single-theme) is implemented; `npm run typecheck`, `npx eslint .`, and the full `npx vitest run` suite stay clean; a PR referencing #1178 is opened with the decision and evidence recorded in this OKF report."
status: "achieved"
---

# Goal: resolver a #1178 (tema órfão pós-reboot)

Investigação ao vivo do preset `cobogo` (instalado via `npm ci` nesta rodada) mostrou zero suporte a modo escuro — nenhuma condição Panda, nenhum semantic token com variante dark, nenhuma consciência de `data-theme`. Com essa evidência, a rodada seguiu o próprio caminho que a issue já autorizava (opção 2 do texto): decisão single-theme, remoção do componente órfão, e um teste de regressão que trava a reintrodução silenciosa do código morto.
