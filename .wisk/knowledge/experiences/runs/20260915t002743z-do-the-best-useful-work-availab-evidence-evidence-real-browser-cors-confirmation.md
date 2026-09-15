---
type: "RunEvidence"
id: "run-evidence/20260915t002743z-do-the-best-useful-work-availab/evidence-real-browser-cors-confirmation"
run: "runs/20260915T002743Z-do-the-best-useful-work-available-in-this-reposi"
kind: "runtime"
reference: "docs/planning/evidence/archive-cors-probe-real-browser.json"
summary: "Real Playwright/Chromium run of scripts/benchmarks/archive_cors_probe.mjs against live archive.org: metadata_endpoint ok=true status=200 type=cors (positive control); download_endpoint_range_request ok=false errorName=TypeError errorMessage='Failed to fetch' -- a real browser cross-origin fetch blocked exactly as the missing Access-Control-Allow-Origin header predicts. Unblocked by adding --ignore-certificate-errors/ignoreHTTPSErrors to the probe script to tolerate this sandbox's forced MITM egress proxy certificate."
goal: "run-goals/20260915t002743z-do-the-best-useful-work-availab/goal-real-browser-cors-confirmation"
---

# RunEvidence
