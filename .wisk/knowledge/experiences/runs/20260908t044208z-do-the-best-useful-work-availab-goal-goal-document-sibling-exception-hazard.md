---
goal: "Add a new generalizable lesson to wiki/continuous-loop-operational-invariants.md: a domain exception introduced for one call site of a shared client function must be audited against every sibling call site that can raise it, not just the one a change happens to touch."
id: "run-goals/20260908t044208z-do-the-best-useful-work-availab/goal-document-sibling-exception-hazard"
kind: "consolidate-knowledge"
rationale: "This round's own fix (PR #1305) found DJENRateLimitedError -- defined once in djen.py, raised by get_caderno_url -- was correctly caught in engine.py and probe.py but silently uncaught in drain.py, permanently killing a worker task on every real 403. This is a distinct but structurally similar hazard to the sync/async dual-calling-convention pattern already documented for circuit_breaker.py (three same-day bugs from the same root cause) -- both are cases where a shared abstraction has multiple independent consumers and a change/exception needs auditing against all of them, not just the one in front of the author. Naming this as its own pattern makes it easier for a future round to recognize the shape (grep for a domain exception's raise sites vs. its except sites) rather than rediscovering it from scratch."
run: "runs/20260908T044208Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "The WikiEntry gains a new paragraph naming this pattern with PR #1305 as evidence, and a future round encountering a similar shared-exception-type audit can cite it directly instead of re-deriving the insight."
type: "RunGoal"
---

# RunGoal
