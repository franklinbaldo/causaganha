---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-02ggxp-decision-status-check-not-size-check"
run_id: "2026-09-09-exciting-mccarthy-02ggxp"
goal_id: "2026-09-09-exciting-mccarthy-02ggxp-goal-djen-segment-range-verification"
question: "Fix the Range-compliance gap by checking resp.status_code == 206 inside _download_segment(), or by checking the final assembled file size against the probe's total_size at the end of download_zip()?"
choice: "Check status_code == 206 inside _download_segment(), at the exact call that issues the Range GET."
rationale: "A status-code check at the point of the request is the minimal, direct fix for the actual defect (the response is accepted as valid without verifying it honored the request that was made) and fails fast per-segment with a clear error message naming which segment misbehaved, before any bytes are written to disk. A final-size check in download_zip() would also catch the corruption, but only after all 4 downloads complete and after already buffering potentially duplicated/oversized bodies in memory, and it conflates two different failure classes (a segment that ignored Range vs. one that legitimately returned fewer bytes for some other reason) into one generic mismatch error. It's also a strictly weaker check: two compensating errors (one segment short, one long by the same amount) could sum to the right total_size while still being wrong. The status-code check has no such blind spot -- 206 is the RFC 7233 contract for a satisfied Range request, and any other status is unconditionally wrong for this call site. Kept the fix to this one check; did not also add a final-size assertion in download_zip(), since it would be redundant validation for a scenario the per-segment check already forecloses."
---

# Decisao: onde verificar a resposta do Range GET

Escolhido verificar `resp.status_code == 206` dentro de `_download_segment()`, no ponto exato da requisicao, em vez de validar o tamanho do arquivo montado ao final de `download_zip()`. E o ponto mais direto, falha rapido por segmento com uma mensagem clara, e fecha a lacuna sem o ponto cego de uma checagem por tamanho total (dois segmentos errados que se compensam ainda bateriam o total).
