---
type: "RunEvidence"
id: "run-evidence/20260914t193005z-do-the-best-useful-work-availab/evidence-curl-confirmation"
run: "runs/20260914T193005Z-do-the-best-useful-work-available-in-this-reposi"
kind: "runtime"
reference: "curl -D - -L -H 'Origin: https://example.com' -H 'Range: bytes=0-99' https://archive.org/download/djen-tjro-2026/comunicacoes.parquet (this session)"
summary: "Independently reconfirmed issue #1482's finding with a third client: the final 206 Partial Content response (after following the 302 to ia800705.us.archive.org) carries no Access-Control-Allow-Origin header, while the equivalent /metadata/djen-tjro-2026/files request does (access-control-allow-origin: *). A cross-origin browser fetch to the download endpoint is blocked deterministically per the Fetch/CORS spec."
goal: "run-goals/20260914t193005z-do-the-best-useful-work-availab/goal-cors-classification"
---

# RunEvidence
