---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-2xmp5l-evidence-runtime-dead-unstyled"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
goal_id: "2026-09-08-exciting-mccarthy-2xmp5l-goal-delete-tribunal-calendar"
kind: "runtime"
reference: "web/src/components/TribunalCalendar.svelte (pre-deletion); grep across web/src, web/src/index.css, web/panda.config.ts"
summary: "Before deleting the file, confirmed both claims behind this round's decision with live grep, not assumption. (1) Zero references: `grep -rn TribunalCalendar\\.svelte web` matched nothing in any .astro/.svelte/.ts file — only this round's own new knowledge files and historical AgentRun reports mention it. (2) Zero CSS backing: grepped every calendar-specific class the component's markup uses (cal-control, cal-control__selectors, cal-control__pick, cal-control__select, cal-control__stats, cal-control__stat, mini-months, mini-month, mini-month__head/__name/__year/__pct/__dows/__dow/__grid, mini-day, mini-day--empty, cal-stat, cal-stat--azul, cal-stat--ocre) across web/src, web/src/index.css, and web/panda.config.ts — none is defined anywhere, including inside the component's own scoped <style> block (which only styles .cal-control__label/.cal-summary/.cal-summary__value). Separately confirmed a live replacement: `grep -rn TribunalCoverageExplorer web/src/pages` shows it imported by web/src/pages/stats.astro; its data comes from lib/tribunalCalendarPartition.ts's loadTribunalCalendarPartition(), which reads the real manifest-backed TribunalCalendarRow contract (web/src/lib/data/contracts.ts), with its own test coverage (TribunalCoverageExplorer.test.ts, tribunalCalendarPartition.test.ts, TribunalCoverageExplorer.payloadBudget.test.ts)."
---

# Evidência runtime: código morto e sem CSS

Antes de apagar, confirmado por grep: (1) nenhuma página/`.svelte`/`.ts` referenciava `TribunalCalendar.svelte`; (2) nenhuma classe usada por seu markup (`cal-control`, `mini-month`, `mini-day`, `cal-stat`, ...) tem definição em lugar nenhum do código, nem no próprio `<style>` escopado do componente. Confirmado também que `TribunalCoverageExplorer.svelte` (usado em `/stats`) já cobre a mesma necessidade com dado real do manifesto.
