---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-e0vvbh-evidence-red-tribunal-coerente"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
goal_id: "2026-09-25-exciting-mccarthy-e0vvbh-goal-tribunal-coerente-manifesto"
kind: "test_red"
reference: "tests/causaganha/processos/test_service.py::TestTribunalCoerenteComUrl (9 casos) e ::test_poisoned_manifest_tribunal_degrades_source_instead_of_trusting"
summary: "RED confirmado em duas rodadas: (1) `uv run pytest -q tests/causaganha/processos/test_service.py -k 'Tribunal or poisoned_manifest_tribunal'` falhou com 9 AttributeError ('module causaganha.processos.service has no attribute _tribunal_da_url/_validar_tribunal_coerente/ArtifactProvenanceError') contra o código anterior, antes de qualquer implementação; (2) o teste de integração `test_poisoned_manifest_tribunal_degrades_source_instead_of_trusting` inicialmente 'passava' pelo motivo errado (o duckdb tentava rede real contra um archive.org fabricado, que falhava por timeout/inacessibilidade neste ambiente, produzindo um aviso genérico de 'indisponível' -- não a rejeição de proveniência pretendida). A asserção foi apertada para exigir a palavra 'incoerente' e a ausência de 'indispon' no aviso, o que voltou a falhar (AssertionError) contra o código anterior -- RED genuíno confirmado antes de implementar."
---

# Evidência RED: coerência de tribunal ainda não implementada
