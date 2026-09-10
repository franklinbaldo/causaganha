---
type: "RunEvidence"
id: "run-evidence/20260910t092514z-do-the-best-useful-work-availab/evidence-red-green-ogimage"
run: "runs/20260910T092514Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "web/src/lib/tribunalOgImage.ts, web/src/lib/tribunalOgImage.test.ts, web/src/pages/publicacoes/[tribunal].astro"
summary: "Read all 14 web/src/pages/*.astro files (938 lines). Found a real defect in publicacoes/[tribunal].astro: it unconditionally built an og:image URL (og/{code}.svg) even for the non-PROD build path and for any tribunal with zipCount=0, but the SVG file is only ever written to public/og/ when both import.meta.env.PROD and zipCount>0 hold -- so Layout.astro's sensible og-image.png fallback (used only when ogImage is falsy) was dead for this page, and social previews for any of the ~90 TRIBUNAIS entries with no archived ZIPs yet would 404. Reproduced RED: wrote tribunalOgImage.test.ts against the original always-return-the-path logic (2 of 3 assertions failed -- npx vitest run src/lib/tribunalOgImage.test.ts -- 'expected og/cjf.svg to be null' and 'expected og/tjro.svg to be null'). Extracted the guard into tribunalOgImagePath(tribunalCode, zipCount, isProdBuild) returning null when either condition fails, wired it into the page (ogImage now becomes undefined so Layout's fallback applies), reran the same test file GREEN (3/3 passed)."
goal: "run-goals/20260910t092514z-do-the-best-useful-work-availab/goal-audit-astro-pages"
---

# RunEvidence
