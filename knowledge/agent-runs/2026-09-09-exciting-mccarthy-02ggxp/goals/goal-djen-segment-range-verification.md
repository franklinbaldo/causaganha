---
type: AgentGoal
id: "2026-09-09-exciting-mccarthy-02ggxp-goal-djen-segment-range-verification"
run_id: "2026-09-09-exciting-mccarthy-02ggxp"
goal: "Make src/djen_backup/djen.py's _download_segment() reject a ranged GET response that isn't 206 Partial Content, instead of silently accepting the body as a valid segment."
rationale: "download_zip() splits large caderno ZIPs (>5MB) into 4 parallel Range GETs and concatenates the raw response bodies with tmp.write(seg), with zero validation that each response actually honored its Range header. DJEN is explicitly fronted by CloudFront (per CLAUDE.md and engine.py's own comments), and CDNs/WAFs are known to answer a ranged request with a full-body 200 under load-shedding, caching, or retry conditions. _retriable_response() in retry.py only retries on 5xx/408/429/(opt-in 400/404) -- a 200 is treated as unconditional success. So a single non-compliant 200 on one of the 4 segment GETs produces a bloated, invalid ZIP that download_zip() returns without error, engine.py's _stage_download() moves straight to the upload staging dir, and archive.py's IA uploader ships to Internet Archive as-is -- corruption only surfaces later if/when someone tries to unzip the published archive. _download_segment/download_zip had zero test coverage anywhere in tests/ before this round (confirmed by grep: every test touching engine.download_zip monkeypatches it away)."
success_signal: "A RED test (respx mock: GET /djen.zip responds 200 instead of 206) fails against unmodified _download_segment (httpx.HTTPError expected, none raised) and passes after the fix; a companion happy-path test (206 response) still returns the segment bytes; the full tests/djen_backup/ suite (119+ tests) stays green; ruff check/format clean; no new vulture findings."
status: "achieved"
---

# Goal: verificar Range compliance em _download_segment

Fechar um gap de corrupcao silenciosa no caminho de download segmentado do DJEN: uma resposta que ignora o header `Range` e devolve `200` com o corpo inteiro era aceita como se fosse o segmento pedido, produzindo um ZIP corrompido que seguia sem erro ate o upload no Internet Archive.
