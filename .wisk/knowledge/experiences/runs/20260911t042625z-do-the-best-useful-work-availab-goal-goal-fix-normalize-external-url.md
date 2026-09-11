---
type: "RunGoal"
id: "run-goals/20260911t042625z-do-the-best-useful-work-availab/goal-fix-normalize-external-url"
run: "runs/20260911T042625Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Fix normalizeExternalUrl in web/src/lib/djen.ts so protocol-relative values (e.g. \"//evil.example.com/x\") are rejected instead of being resolved onto the attacker-supplied host, and add djen.test.ts covering it."
rationale: "An Explore-agent defect sweep of untested web/src/lib/*.ts files (this round's active-handoffs/active-skills readings found no in-flight handoff or prior skill to resume, so a fresh sweep was the best available work) found that normalizeExternalUrl treats any string starting with '/' as a DJEN-relative path, including protocol-relative '//host/path' values; new URL(raw, 'https://comunicaapi.pje.jus.br') resolves those onto the attacker's host because WHATWG URL parsing treats a leading '//' as a network-path reference. The resulting pub.link is what PublicationCard.svelte renders as the clickable 'Inteiro teor' link, so a malicious or compromised upstream value silently redirects users off the trusted DJEN domain."
success_signal: "web/src/lib/djen.test.ts exists with a case asserting normalizeExternalUrl('//evil.example.com/malware') is undefined (or otherwise never resolves to a evil.example.com URL); the test fails against the current implementation (RED), passes after the fix (GREEN); uv run vitest run for djen.test.ts is green; PR opened."
status: "active"
---

# RunGoal
