---
type: "RunDecision"
id: "run-decisions/20260908t202452z-do-the-best-useful-work-availab/decision-datajud-decisoes-clean-fix-scope"
run: "runs/20260908T202452Z-do-the-best-useful-work-available-in-this-reposi"
question: "Widened audit found src/datajud, causaganha/decisoes, causaganha/processos mostly clean, with two candidates from the auditor: (1) datasets_consultados overcounting skipped STJ in search.py, (2) dead data14_bound helper in datajud/models.py. Which to act on this round?"
decision: "Fix (1) only: it is a real, user-visible logic bug (decisoes_buscar's MCP resumo string reports an inflated dataset count including a source the same response's limitacoes explicitly says was skipped), it is untested, and it fits this loop's TDD contract cleanly with a small, local, reviewable diff. Leave (2) (data14_bound dead code) unaddressed this round."
rationale: "data14_bound causes zero incorrect behavior today (no caller anywhere, fully unit-tested in isolation) -- removing speculative-but-harmless code is lower priority than shipping a real reporting-bug fix, and bundling an unrelated dead-code deletion into the same PR would widen the diff without a shared root cause. Recorded as this round's next_move instead."
---

# RunDecision
