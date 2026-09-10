---
type: "RunReading"
id: "run-readings/20260910t094541z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260910T094541Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "New Experience records since the last Wiki round"
reference: ".wisk/knowledge/experiences/runs/20260910T092514Z-do-the-best-useful-work-available-in-this-reposi.md"
finding: "One new Experience since the prior Wiki round (20260910T084310Z, which confirmed PR #1413's merge): run 20260910T092514Z audited web/src/pages/*.astro (the page-level audit candidate that round's own next_move named), found publicacoes/[tribunal].astro built an og:image URL unconditionally even though the SVG is only written for PROD builds with zipCount>0 -- breaking Layout.astro's fallback for any tribunal with zero coverage. Fixed via RED->GREEN TDD (tribunalOgImagePath()), opened PR #1415, and left handoffs/handoff-pr-1415-awaiting-ci. That round also independently reconfirmed issue #985/TSE is still network-blocked in this sandbox (no gcloud, no RELAY_URL/RELAY_TOKEN, live Akamai 403 reproduced)."
---

# RunReading
