---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-aezdb9-evidence-red-test"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
goal_id: "2026-09-10-exciting-mccarthy-aezdb9-goal-ia-rate-limit-fallback"
kind: "test_red"
reference: "uv run pytest tests/djen_backup/test_ia_rate_limit_parsing.py -q, run against archive.py before the fix"
summary: "Collection error: ImportError: cannot import name '_parse_ia_max_rate' from 'djen_backup.archive'. Confirms the test targets behavior that does not yet exist in the unmodified module."
---

# Evidência RED

```
==================================== ERRORS ====================================
_______ ERROR collecting tests/djen_backup/test_ia_rate_limit_parsing.py _______
ImportError while importing test module '/home/user/causaganha/tests/djen_backup/test_ia_rate_limit_parsing.py'.
tests/djen_backup/test_ia_rate_limit_parsing.py:21: in <module>
    from djen_backup.archive import _parse_ia_max_rate
E   ImportError: cannot import name '_parse_ia_max_rate' from 'djen_backup.archive' (/home/user/causaganha/src/djen_backup/archive.py)
```
