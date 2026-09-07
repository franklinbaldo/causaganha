---
type: "RunEvidence"
id: "run-evidence/20260907t082458z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-red-then-green-comunicacoes-output"
run: "runs/20260907T082458Z-fa-a-o-melhor-avan-o-poss-vel-no-reposit-rio-fra"
kind: "execution"
reference: "tests/causaganha_cli/test_causaganha_cli_main.py + src/causaganha_cli/__main__.py diff"
summary: "RED: test_comunicacoes_rejects_invalid_output_format failed with 'DID NOT RAISE ValueError' on the unmodified CLI (comunicacoes(output=\"xml\") silently rendered a table instead of rejecting the value, unlike query() which validates the same parameter). GREEN: after adding 'if output not in {\"table\", \"json\"}: raise ValueError(...)' to comunicacoes() (mirroring query()'s existing check), all 13 tests in the new file pass, including the other 12 that were already green pre-fix (connection success/HTTP-error propagation, query table/json rendering and validation, comunicacoes defaults/filtering/quote-escaping/limit-bounds)."
goal: "run-goals/20260907t082458z-fa-a-o-melhor-avan-o-poss-vel-n/goal-test-and-fix-causaganha-cli"
---

# RunEvidence
