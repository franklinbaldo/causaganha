---
type: "RunReading"
id: "run-readings/20260907t214503z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260907T214503Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "This same-day round-family's recent Experience runs"
reference: ".wisk/knowledge/experiences/runs/"
finding: "Run 20260907T212647Z merged PR #1291 (concurrent sibling's probe.py 403 fix) and then, following the round-family's own next_move lead (circuit_breaker.py had 2 prior same-day bug fixes: c352943, b383135), did a fresh adversarial read of that file against its real callers. Found a third real gap: record_failure() only reopened the circuit with a doubled timeout when self._probing was set, which only the async allow_request() path ever sets -- ia_s3.py's sync path (is_open + record_failure only) never triggers a reopen on a failed half-open probe, letting sync callers retry an unhealthy IA host at unlimited rate with zero backoff. Fixed via RED->GREEN TDD (new BDD scenario), landed as PR #1293, merged this round (squash cf92afd)."
---

# RunReading
