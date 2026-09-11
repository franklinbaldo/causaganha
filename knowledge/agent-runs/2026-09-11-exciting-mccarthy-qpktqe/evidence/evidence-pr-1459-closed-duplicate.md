---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-pr-1459-closed-duplicate"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
kind: "other"
reference: "https://github.com/franklinbaldo/causaganha/pull/1459#issuecomment-5629140713; https://github.com/franklinbaldo/causaganha/pull/1458 (merged as 5dfe0f3)"
summary: "While PR #1459's CI was still running, a concurrent session (session_01ULmduThttzhfrox853uFgX -- the same session that authored PR #1456/#1457, apparently continuing to work after this session's own reading-prs.md had already recorded #1457 as merged) opened and merged PR #1458, which fixed the identical bug the identical way: isValidCalendarDate's Date.UTC(...) round-trip probe swapped for `new Date(0); asUtc.setUTCFullYear(...)`, plus the same two regression-test assertions (toIsoDate('0001-01-01') === '0001-01-01', toIsoDate('0099-12-31') === '0099-12-31'). Both sessions independently reached the same Codex finding on PR #1457 and the same fix at essentially the same moment -- a genuine race, not a mistake by either side. Confirmed via `git show 5dfe0f3 -- web/src/lib/processoCnj.ts web/src/lib/processoCnj.test.ts`: functionally identical diff (only comment wording and test description text differ). PR #1459 closed as a duplicate with an explanatory comment; unsubscribed from its activity. This session's branch was reset to origin/main (which already carries #1458's fix) and only this round's own AgentRun report tree was kept."
---

# PR #1459 fechada como duplicata

Enquanto a CI da #1459 ainda rodava, uma sessão concorrente mesclou a PR #1458 com o fix idêntico (mesmo bug, mesma solução `setUTCFullYear`, mesmos dois asserts de regressão) contra a mesma descoberta do Codex na PR #1457. Corrida real entre duas sessões, não um erro de nenhuma das duas. Fechada como duplicata; branch resetado sobre `main` (que já carrega a correção via #1458), mantendo apenas o relatório `AgentRun` desta rodada.
