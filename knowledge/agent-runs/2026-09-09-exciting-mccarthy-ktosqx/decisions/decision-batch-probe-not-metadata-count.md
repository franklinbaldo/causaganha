---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-ktosqx-decision-batch-probe-not-metadata-count"
run_id: "2026-09-09-exciting-mccarthy-ktosqx"
goal_id: "2026-09-09-exciting-mccarthy-ktosqx-goal-datedetail-page-probe-cap"
question: "The component already fetches IA item metadata (meta.files) into itemFileCount before probing pages -- should the fix derive totalPages from that instead of growing the HEAD-probe batches?"
choice: "No -- keep discovering pages via HEAD probes, just remove the fixed cap by growing in batches of 30 instead of stopping after one fixed batch."
rationale: "itemFileCount is computed by filtering meta.files (the whole djen-{tribunal}-{year} IA item's file list) to non-system data files -- it counts every ZIP + JSON shard for every date in that tribunal's whole year, not just this one date's shards. There is no reliable way to isolate this date's own page count from that aggregate list without parsing every filename in it (data_files.filter(f => f.name matches this date's shard pattern)), which is a larger, riskier change (touches the metadata-fetch path, its error handling, and the filename convention) for a fix that the batch-probe approach already solves with a minimal, local change to the existing probe loop. The batch-probe fix also preserves the exact existing behavior for the common case (<=30 pages: identical single round-trip, identical result) and only adds probing cost in the boundary case where more pages genuinely exist -- exactly the case that needs it. Deriving totalPages from itemFileCount is a plausible future simplification if a later round wants to cut network round-trips, but it is a separate, larger change not required to fix this bug, and CLAUDE.md's general instructions discourage scope creep beyond what a fix needs."
---

# Decisão: sondagem em lotes, não contagem via metadados do item

`itemFileCount` já buscado da API de metadados do IA cobre o item do ano inteiro (todas as datas daquele tribunal), não só esta data -- não dá para derivar `totalPages` dali sem analisar nomes de arquivo, uma mudança maior e fora do escopo deste bug. A sondagem em lotes crescentes resolve o problema com uma mudança mínima e local, preservando o comportamento idêntico para o caso comum (≤30 páginas).
