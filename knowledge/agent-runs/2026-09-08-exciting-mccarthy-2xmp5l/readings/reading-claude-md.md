---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-2xmp5l-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read in full at round start. Correctness rules (djen_raw is transport-only, never a verdict on availability; a 200-without-URL 'Sem comunicações' body is absent exactly like 404/400; 403 must never be treated as absent) are unchanged since the prior round and out of scope for this round's selected work, which is a web/ frontend cleanup. The relevant section this round is 'CSS token boundary' (lines 67-76): it names exactly four legacy Svelte islands that predate the Panda/Cobogó reboot and still consume `--papel-*`/`--s-*` custom properties via scoped `<style>` blocks instead of `css()` — `ProcessoLookup.svelte`, `PublicationSearch.svelte`, `SavedConsultations.svelte`, `TribunalCalendar.svelte`. Investigation this round (see reading-okf.md and decision-delete-tribunal-calendar.md) found `TribunalCalendar.svelte` is dead code: unreferenced by any .astro page, and its own scoped `<style>` block does not even define the `cal-control`/`mini-month`/`mini-day`/`cal-stat` classes its markup uses (no match anywhere else in web/src either) — so this document's premise that it is a 'maintained' legacy island is itself stale and needed correcting as part of this round's diff. No other CLAUDE.md rule was touched."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. A seção relevante para o trabalho desta rodada é 'CSS token boundary', que lista `TribunalCalendar.svelte` como uma das quatro ilhas Svelte legadas "mantidas". A investigação desta rodada mostrou que esse componente é código morto (não referenciado por nenhuma página `.astro`) e nem sequer possui CSS próprio para as classes que usa — a premissa do CLAUDE.md estava desatualizada e foi corrigida como parte da mudança.
