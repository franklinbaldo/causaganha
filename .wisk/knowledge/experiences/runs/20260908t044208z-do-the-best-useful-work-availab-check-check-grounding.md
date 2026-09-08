---
type: "RunCheck"
id: "run-checks/20260908t044208z-do-the-best-useful-work-availab/check-grounding"
run: "runs/20260908T044208Z-do-the-best-useful-work-available-in-this-reposi"
kind: "grounding"
procedure: "Verify the new WikiEntry paragraph's claims trace back to real Experience evidence (this round's own RED->GREEN fix and PR #1305), and that it doesn't collapse or contradict the existing sync/async dual-calling-convention paragraph it's contrasted against."
result: "Every factual claim in the new paragraph (DJENRateLimitedError's definition site, the two callers that already caught it, drain.py's omission, the RED->GREEN test, PR #1305's squash sha) is directly traceable to this round's own run-goals/run-evidence/run-checks records and the merged PR diff, not invented. The paragraph explicitly names how the new pattern differs from the existing sync/async hazard (call-site coverage vs. calling-convention) rather than conflating them, preserving the distinction per the RunSpec's completion_notes."
status: "pass"
evidence: "run-evidence/20260908t044208z-do-the-best-useful-work-availab/evidence-wiki-diff"
goal: "run-goals/20260908t044208z-do-the-best-useful-work-availab/goal-document-sibling-exception-hazard"
---

# RunCheck
