---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-02ggxp-evidence-diff"
run_id: "2026-09-09-exciting-mccarthy-02ggxp"
goal_id: "2026-09-09-exciting-mccarthy-02ggxp-goal-djen-segment-range-verification"
kind: "diff"
reference: "src/djen_backup/djen.py (HTTP_PARTIAL_CONTENT constant, _raise_not_partial helper, one status check in _download_segment); tests/djen_backup/test_download_segment.py (new file, 2 tests)"
summary: "Minimal, 3-hunk diff in djen.py: (1) added HTTP_PARTIAL_CONTENT = 206 alongside the existing HTTP_* status constants; (2) added a _raise_not_partial(status_code) helper mirroring the file's existing _raise_server_error/_raise_not_found pattern (keeps ruff TRY301 happy -- raises extracted to inner functions per CLAUDE.md); (3) one new check in _download_segment() after the existing raise_for_status() call: if resp.status_code != HTTP_PARTIAL_CONTENT, call _raise_not_partial(resp.status_code). No other function touched; download_zip()'s assembly logic and _download_simple()'s non-ranged fallback are unchanged."
---

# Evidencia: diff

Diff minimo e localizado em `_download_segment()`: uma constante nova, um helper de raise, e uma checagem de status apos o `raise_for_status()` existente. Nenhuma outra funcao alterada.
