---
type: "RunReading"
id: "run-readings/20260910t134021z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260910T134021Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "run-outcomes/20260910t132702z-do-the-best-useful-work-availab/outcome-final"
reference: "../experiences/runs/20260910t132702z-do-the-best-useful-work-availab-outcome-outcome-final.md"
finding: "The Experience round this session ran earlier (runs/20260910T132702Z) needed 'uv run wisk init .' first (fresh checkout, zero SessionType records loaded, per the wiki's already-documented gotcha), then audited two leads from the prior round's next_move: the year-boundary discovery bug class was re-checked and ruled out elsewhere in the codebase, while a scripts/*.py long-tail audit found scripts/annotate_with_llm.py's two per-item LLM-call bulkheads (lines 449, 489) missing the docs/adr/0011 citation CLAUDE.md requires, despite already satisfying the ADR's substantive bulkhead test. Fixed RED->GREEN with a scoped regression test, landed as PR #1423, handoff handoffs/handoff-pr-1423-awaiting-ci left for this continuation."
---

# RunReading
