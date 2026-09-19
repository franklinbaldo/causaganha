---
type: AgentCheck
id: "2026-09-19-exciting-mccarthy-gbf44b-check-pytest-segmenter"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
command: "uv run pytest -q tests/segmenter_dataset"
result: "passed"
evidence_id: "2026-09-19-exciting-mccarthy-gbf44b-evidence-batch22-ingested"
summary: "First run: 1 failure (test_real_store_has_at_most_the_one_known_collapsed_false_positive, a hardcoded allowlist regression guard not yet aware of batch22's new document). Triaged and fixed by extending the allowlist with a documented, source-verified reason. Second run: 100% pass, no failures."
---

# Check: pytest da suite do segmentador, lote 22

Primeira rodada completa (apos a ingestao real) rodou ate ~92% dos
testes e falhou em
`test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive`
-- um guard de regressao com um allowlist hardcoded de `doc_id`s
conhecidos como falsos positivos do audit semantico, que ainda nao
conhecia o novo documento do lote 22. Isolei a falha com `pytest -x`,
li o traceback completo, e verifiquei manualmente contra o
`texto_limpo` bruto (nao assumindo que era um falso positivo so porque
parecia com os outros) antes de estender o allowlist com uma razao
documentada (ver `decision-extend-collapsed-allowlist`).

Segunda rodada completa apos a correcao: 100% verde, 0 falhas
(confirmado apos aguardar a suite completa, que continua lenta o
suficiente em ~173 documentos para levar varios minutos -- mesmo
padrao ja documentado nos lotes 20/21).
