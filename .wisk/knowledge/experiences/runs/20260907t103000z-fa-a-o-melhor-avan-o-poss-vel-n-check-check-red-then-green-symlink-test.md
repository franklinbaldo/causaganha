---
type: "RunCheck"
id: "run-checks/20260907t103000z-fa-a-o-melhor-avan-o-poss-vel-n/check-red-then-green-symlink-test"
run: "runs/20260907T103000Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "verification"
procedure: "uv run pytest tests/test_wikiskill_bundle.py -q, executado antes (RED) e depois (GREEN) de 'rm -rf .wisk; ln -s .wikiskill .wisk'"
result: "Antes: 1 failed (test_wisk_root_is_a_symlink_into_wikiskill), 2 passed. Depois: 3 passed."
status: "pass"
evidence: "evidence-red-symlink-test"
goal: "goal-fix-wisk-bootstrap-path"
---

# RunCheck
