---
type: "RunEvidence"
id: "run-evidence/20260907t103000z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-red-symlink-test"
run: "runs/20260907T103000Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "execution"
reference: "local: uv run pytest tests/test_wikiskill_bundle.py -q (antes da correção, com .wisk como diretório real gerado por 'uv run wisk init .')"
summary: "RED confirmado: test_wisk_root_is_a_symlink_into_wikiskill falhou com AssertionError ('.wisk' must be a tracked symlink...), pois PosixPath('.wisk').is_symlink() era False (era um diretório real, gitignorado)."
goal: "goal-fix-wisk-bootstrap-path"
---

# RunEvidence
