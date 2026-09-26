---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-kgxf50-decision-preserve-audit-allowlist-precedent"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
question: "tests/segmenter_dataset/test_segmenter_audit_scripts.py's collapsed-false-positive allowlist failed after adjudicating doc_3b0be436ba6753185997c37b2b6b9765 (TJSE), asserting an exact 7-document set that no longer matched live scan results (6 documents) once this document's second annotation existed. Fix the review's content, or fix the test?"
choice: "Neither annotation's fundamentacao_legal-vs-acordao_decisorio_fim choice was a defect to silently pick a side on without checking precedent first -- re-read the test's own docstring, which already documented (before this round) a deliberate reason for the original single annotation NOT tagging the final citation as fundamentacao_legal: it is verbatim-identical to the acordao_decisorio's own closing anchor, and double-tagging one span with two categories is the guideline's own anti-pattern. Reverted the review's resolution to match that documented precedent (acordao_decisorio_fim, not a second fundamentacao_legal), then fixed the test's allowlist (not the review) to drop this doc_id with a documented reason: the SECOND (this round's) annotation, used by find_anti_patterns's _latest_per_document heuristic, genuinely tags both citations distinctly (a legitimate independent reading, not a defect), so the annotation-level heuristic no longer reproduces the historical false positive -- independent of what the accepted review says."
rationale: "The review and the test were both potentially editable, but only one edit was correct: the test's own docstring already contained the exact reasoning needed, written by an earlier round specifically about this document -- ignoring it and picking B's classification would have silently overwritten a deliberate, documented precedent with no new information to justify the change. The test's assertion, by contrast, was never about the review at all (find_anti_patterns scans raw ANNOTATIONS, not reviews) -- it is a live fact about the corpus's annotation-level state that necessarily shifts whenever any allowlisted document gets a second annotation, exactly analogous to the governance-status test's own documented instruction to update counts rather than treat a change as a failure."
---

# Decision: preserve pre-existing annotation precedent, update the test instead

Caught by re-running `tests/segmenter_dataset` before finalizing: the
audit allowlist test failed, but reading its own docstring revealed the
original annotator had already deliberately chosen not to double-tag
the final citation, for a documented reason specific to this exact
document. Reverted the review to match that precedent instead of
adopting the second annotation's alternate (also valid, but
undocumented-as-preferred) classification, then updated the test's
allowlist -- which tracks annotation-level heuristic behavior, not
review content -- to reflect that a second annotation now exists.
