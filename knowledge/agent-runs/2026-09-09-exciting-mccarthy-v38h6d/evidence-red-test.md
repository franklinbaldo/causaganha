---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-v38h6d-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-v38h6d"
goal_id: "2026-09-09-exciting-mccarthy-v38h6d-goal-check-only-no-io"
kind: "test_red"
reference: "tests/djen_backup/test_check_only_no_io.py::test_check_only_never_downloads_or_uploads_backlog, run via `uv run pytest tests/djen_backup/test_check_only_no_io.py -q -s` against unmodified src/djen_backup/engine.py"
summary: "Seeded a SyncManifest with one entry (TJSP/2024-01-03, djen_status='available', djen_raw='200', ia_status='') and ran engine.run_pipeline with check_only=True, monkeypatching _stage_download/upload_zip to record a call and raise. Failed as expected: AssertionError: assert {'download': True, 'upload': False} == {'download': False, 'upload': False} -- confirming the unmodified pipeline feeds an existing backlog entry into the download worker even under check_only=True, contradicting the documented 'no I/O' contract. (An earlier draft of this same test that relied on the module's default 5-second deadline instead of restoring real asyncio.sleep passed vacuously in both the buggy and fixed code, because tests/djen_backup/conftest.py's autouse _fast_sleep fixture fast-forwards any sleep()>0.05s, collapsing the deadline before any worker got a scheduling turn -- the test was corrected to restore real sleep for its own deadline_monitor wait before this RED run.)"
---

# Evidencia RED

O teste falha contra o `engine.py` original: o worker de download e efetivamente chamado (`called['download'] == True`) mesmo com `check_only=True` e sem nenhum item "unknown" na fila de checagem -- confirmando que o backlog existente (`djen_status="available", ia_status=""`) e alimentado para download/upload independentemente do modo "somente checagem".
