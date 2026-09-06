---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-b0lycs-evidence-build-payload-before-after"
run_id: "2026-09-06-exciting-mccarthy-b0lycs"
goal_id: "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
kind: "runtime"
reference: "npm run build (web/), before vs. after this round's changes, with CI's own stub data files (test.yml's 'Stub pipeline-generated data files' step, reproduced locally — no real manifest.parquet available in this sandbox)"
summary: "Built /stats twice against the same 2-row tribunal_calendar.json stub: once with this round's changes stashed out (old code) and once with them restored (new code). OLD dist/stats.html: 15412 bytes, contains the literal string 'calendarRows' once (the astro-island's serialized props attribute for the client:only component) — confirming client:only does serialize this prop into the page even though the component never renders server-side. NEW dist/stats.html: 15096 bytes, zero occurrences of 'calendarRows' anywhere. With the 2-row stub the byte delta is small by construction, but the mechanism is what #1191 flagged: with the real canonical contract (~13.9MB per PR #1189's own AgentRun measurement), that same serialized prop would scale with the full archive instead of being absent. Also confirmed the fix actually ships end-to-end: ran scripts.render_queries._partition_tribunal_calendar directly against the stub tribunal_calendar.json, then rebuilt — dist/data/tribunal_calendar_by_tribunal/placeholder.json exists in the final dist/ output (proving Astro's public/ copy step, which runs before page frontmatter, does pick up files render_queries.py writes beforehand — unlike the Astro-frontmatter-fs-write approach tried and rejected first, see the accompanying AgentDecision)."
---

# Evidência: build antes/depois do payload de /stats

Build de `/stats` com e sem a correção, mesmo stub de 2 linhas: `calendarRows` aparece uma vez em `dist/stats.html` na versão antiga (prop serializada da ilha `client:only`) e zero vezes na nova. Particionamento confirmado chegando ao `dist/` final após mover a geração para `render_queries.py`.
