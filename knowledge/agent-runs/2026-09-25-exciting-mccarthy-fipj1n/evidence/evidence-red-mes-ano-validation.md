---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-fipj1n-evidence-red-mes-ano-validation"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
kind: "test_red"
reference: "tests/tjro_juris/test_juris_manifest.py::test_load_text_rejects_malformed_mes_ano (8 casos), tests/causaganha/decisoes/test_published.py::test_juris_discovery_rejects_manifest_with_path_traversal_mes_ano"
summary: "Reprodução ao vivo antes de qualquer mudança de produção: `discover_published_juris_datasets` com mes_ano='2024-01/../../secret-item' produz a URL 'https://archive.org/download/tjro-juris-2024/2024-01/../../secret-item-AC%C3%93RD%C3%83O.parquet' (path traversal sobrevivente, capturado literalmente via uv run python3 -c). 9 testes novos escritos primeiro contra a API alvo (ManifestFormatError ainda não levantado por nenhum mes_ano malformado): uv run pytest -q tests/tjro_juris/test_juris_manifest.py tests/causaganha/decisoes/test_published.py antes da mudança de produção — 8 falhas 'DID NOT RAISE ManifestFormatError' (parametrizado: '2024-01/../../secret-item', '2024-01/etc/passwd', '../../2024-01', '2024-1', '2024-13', 'abcd-ef', '', mais o teste em test_published.py). Os testes pré-existentes dos dois arquivos continuaram passando, confirmando que o RED é isolado ao novo comportamento."
---

# Evidência RED: `mes_ano` malformado não é rejeitado

Antes da mudança de produção, `ManifestJuris.load_text` aceita qualquer
`mes_ano`, incluindo valores com `/../` que sobrevivem intactos até a URL
final que `read_parquet` consome — reproduzido ao vivo e capturado
literalmente, não apenas inferido. 8 casos parametrizados + 1 teste em
`test_published.py` falham com "DID NOT RAISE ManifestFormatError".
