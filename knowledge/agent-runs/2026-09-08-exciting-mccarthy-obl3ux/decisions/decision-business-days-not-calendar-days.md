---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-obl3ux-decision-business-days-not-calendar-days"
run_id: "2026-09-08-exciting-mccarthy-obl3ux"
goal_id: "2026-09-08-exciting-mccarthy-obl3ux-goal-fix-weekend-inflated-completion"
question: "Should 'expected days' in the tribunal completion math count every calendar day (current behavior) or only business days (Mon-Fri, matching the manifest's own build rule)?"
choice: "Business days only. Added businessDaysBetweenIso()/isBusinessDayIso() to web/src/lib/dateUtils.ts as the single shared implementation of the manifest's weekday rule, used by both TribunalDetail.svelte's expectedDays and velocityCalc.ts's coverage-window day counters."
rationale: "The manifest (src/djen_backup/manifest.py's SyncManifest.build()) is the actual source of truth for what 'expected' means in this pipeline, and it deliberately never creates weekend rows -- DJEN publication days are business days. Counting calendar days in the frontend creates a structural mismatch: the numerator (coverageSize+absentCount) can never include a weekend day because none exist in the data, but the old denominator (calendar days) did, so completion was mathematically capped at ~5/7 regardless of real backlog. Switching the denominator to business days makes the frontend's model consistent with the backend's actual data-generating process, which is also the more 'correct' definition since DJEN itself does not publish on weekends -- there is no real work being measured on those days at all. Fixing at the shared dateUtils.ts level (rather than duplicating the weekday check separately in TribunalDetail.svelte and velocityCalc.ts) keeps the two call sites from drifting apart the way daysBetweenIso already was duplicated pre-fix."
---

# Decisao: contar dias uteis, nao dias de calendario

O manifesto so cria linhas para dias uteis. Contar dias de calendario no frontend criava uma incompatibilidade estrutural: o numerador nunca pode incluir fim de semana (nao existe no dado), mas o denominador antigo incluia, limitando a completude a ~71% para qualquer tribunal. Adicionada uma unica implementacao compartilhada (`businessDaysBetweenIso`/`isBusinessDayIso` em `dateUtils.ts`) usada tanto por `TribunalDetail.svelte` quanto por `velocityCalc.ts`.
