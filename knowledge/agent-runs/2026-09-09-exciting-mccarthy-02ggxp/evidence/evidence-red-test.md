---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-02ggxp-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-02ggxp"
goal_id: "2026-09-09-exciting-mccarthy-02ggxp-goal-djen-segment-range-verification"
kind: "test_red"
reference: "tests/djen_backup/test_download_segment.py::test_download_segment_rejects_response_that_ignores_range_header, run against unmodified src/djen_backup/djen.py"
summary: "`uv run pytest tests/djen_backup/test_download_segment.py -q` against pre-fix djen.py: FAILED -- pytest.raises(httpx.HTTPError) block reported 'Failed: DID NOT RAISE HTTPError'. Confirms _download_segment() silently accepted a 200 response to a Range GET (respx mock: GET https://djen.example/djen.zip -> 200, body b'whole-file-body') and returned its content as if it were the requested byte range, exactly the corruption path described in the goal."
---

# Evidencia: teste RED

`test_download_segment_rejects_response_that_ignores_range_header` falhou com `DID NOT RAISE HTTPError` contra o codigo original, provando que uma resposta 200 (ignorando o header `Range`) era aceita sem erro.
