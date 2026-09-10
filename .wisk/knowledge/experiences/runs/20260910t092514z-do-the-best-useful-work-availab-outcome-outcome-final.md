---
type: "RunOutcome"
id: "run-outcomes/20260910t092514z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260910T092514Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Read all 14 web/src/pages/*.astro files as this round's audit target (named by the prior round's RunOutcome as one of three next-move candidates; issue #985/TSE was independently reproduced as still network-blocked from this sandbox too -- no gcloud, no RELAY_URL/RELAY_TOKEN env, real Akamai 403 confirmed live via curl -- so it was not this round's actionable path). Found a real defect in publicacoes/[tribunal].astro: the og:image URL was built unconditionally even though the SVG behind it is only written in a PROD build for tribunals with zipCount>0, so Layout.astro's og-image.png fallback was dead and social previews 404 for any of the ~90 TRIBUNAIS entries without archived ZIPs yet. Reproduced RED against the original logic (2/3 assertions failed), extracted tribunalOgImagePath() and fixed the page, GREEN after (3/3). Full validation clean: npm lint/typecheck/test (513 tests) and uv ruff/pytest (full suite, 1 pre-existing skip). Opened PR #1415, subscribed this session to its activity, and recorded handoffs/handoff-pr-1415-awaiting-ci for CI/merge continuation."
next_move: "Immediate: drive PR #1415 to green and merge (this session is subscribed and will react to CI/review events). Beyond that, the prior round's other two audit candidates remain open: the deployment/relay/ Cloud Function source itself (only its consumers -- stj_acordaos, tjro_juris, tse_processual -- have been audited so far; the function's own code was read this round while investigating #985 and looks sound, but hasn't been through the same defect-hunting pass as the page audit), and whether anything beyond scripts/inspect_tse_processual.py and scripts/profile_tse_processual.py actually needs the TSE relay allowlist validated live -- that step still requires either gcloud deploy credentials or a GitHub Actions run with RELAY_URL/RELAY_TOKEN, neither available to this sandbox; a future round with GCP access should redeploy deployment/relay/function with the widened *.tse.jus.br allowlist and confirm live from southamerica-east1 before #985 can proceed to schema/join proof."
goals_advanced: ["run-goals/20260910t092514z-do-the-best-useful-work-availab/goal-audit-astro-pages"]
evidence: ["run-evidence/20260910t092514z-do-the-best-useful-work-availab/evidence-red-green-ogimage"]
checks: ["run-checks/20260910t092514z-do-the-best-useful-work-availab/check-verification"]
---

# RunOutcome
