---
type: "RunEvidence"
id: "run-evidence/20260910t072709z-do-the-best-useful-work-availab/evidence-allowlist-red-green"
run: "runs/20260910T072709Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/deployment/relay/test_main.py::test_host_allowed_accepts_allowlisted_hosts, deployment/relay/function/main.py"
summary: "RED: added cdn.tse.jus.br/dadosabertos.tse.jus.br/tse.jus.br cases to the existing accept/reject parametrized tests in tests/deployment/relay/test_main.py; 4 cases failed against unmodified main.py (_host_allowed rejected every TSE host). GREEN: added '.tse.jus.br' to _ALLOWED_SUFFIXES and 'tse.jus.br' to _ALLOWED_EXACT in deployment/relay/function/main.py, plus a module-docstring caveat that this widened allowlist is not yet validated live against TSE's Akamai front the way STJ/TJRO were. Full tests/deployment/relay/test_main.py (30 tests) now passes."
goal: "run-goals/20260910t072709z-do-the-best-useful-work-availab/goal-tse-relay-wiring"
---

# RunEvidence
