---
type: "RunEvidence"
id: "run-evidence/20260925t012524z-do-the-best-useful-work-availab/evidence-1610-artifact-url-validation"
run: "runs/20260925T012524Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/causaganha/processos/test_service.py::TestValidateArtifactUrl e test_poisoned_manifest_url_degrades_source_instead_of_crashing"
summary: "TDD RED->GREEN para issue #1610: 12 testes novos (11 unitários de _validate_artifact_url + 1 de integração via buscar_processo) confirmados RED (AttributeError: service tinha nenhum _validate_artifact_url/ArtifactUrlError) antes da implementação; GREEN após implementar o validador central (https-only, host archive.org, path /download/*.parquet, sem query/fragment, sem aspas simples -- bloqueia a injeção de SQL/URL via arquivo_ia_url de um indice_processual.parquet comprometido) e ligá-lo em _fonte_urls, que agora descarta (com aviso, sem propagar exceção) qualquer URL inválida antes de _djen_sql/_juris_sql/_stj_sql/_datajud_sql. Suíte completa do módulo: 31/31 passed. uv run pytest -q (repo inteiro): green (exit 0). ruff check e ruff format --check limpos."
---

# RunEvidence
