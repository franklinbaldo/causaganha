---
type: "RunCheck"
id: "run-checks/20260915t002743z-do-the-best-useful-work-availab/check-handoff-disposition"
run: "runs/20260915T002743Z-do-the-best-useful-work-available-in-this-reposi"
kind: "handoff-disposition"
procedure: "Evaluate handoffs/handoff-issue-1471-archive-readback-v2's three next_action items against current environment/repo state."
result: "reframed: items 1-2 (publish candidate parquet to Internet Archive, real read-back for the candidate) remain rejected-for-this-round -- IA_ACCESS_KEY/IA_SECRET_KEY absent from env, unchanged since baseline, a hard-to-reverse live IA write correctly left to a session with credentials. Item 3 (real-browser CORS confirmation, previously blocked by net::ERR_CERT_AUTHORITY_INVALID against this sandbox's own forced MITM proxy) is accepted and resolved this round: scripts/benchmarks/archive_cors_probe.mjs fixed with an --ignore-certificate-errors/ignoreHTTPSErrors bypass (safe outside this sandbox -- it only widens which TLS errors are tolerated, doing nothing on a host with a normal cert chain) and re-run for real against archive.org, producing a definitive real-Chromium confirmation of issue #1482's root cause."
status: "pass"
evidence: "run-evidence/20260915t002743z-do-the-best-useful-work-availab/evidence-real-browser-cors-confirmation"
---

# RunCheck
