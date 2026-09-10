---
type: "RunReading"
id: "run-readings/20260910t043903z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260910T043903Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: "Existing WikiEntry, 20 pattern paragraphs, most recently the squash-merge branch-continuation hazard (twentieth) and the sibling-config-flag family (nineteenth: check_only -> upload_only -> dead-flags cleanup)."
finding: "No paragraph yet names the specific hazard this round found: a prior round's own RunOutcome can assert a flag is 'verified genuinely read/honored' after checking only that the field is read somewhere, without checking that every documented code path actually enforces it -- a narrower, and importantly different, claim than 'the whole contract holds'. This is a variant of the already-named sibling-code-path family (nineteenth pattern) but sharpens it in a new direction: the earlier instances found an *unaudited* sibling; this one found a *previously audited and declared clean* sibling that was actually still broken, because the audit's own success criterion was weaker than the bug it was supposed to rule out."
---

# RunReading
