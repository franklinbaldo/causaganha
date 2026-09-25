---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-fipj1n-evidence-green-mes-ano-validation"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
kind: "test_green"
reference: "src/tjro_juris/manifest.py (_MES_ANO_PATTERN, _validate_mes_ano), tests/tjro_juris/test_juris_manifest.py, tests/causaganha/decisoes/test_published.py"
summary: "Após adicionar _MES_ANO_PATTERN=re.compile(r'^\\d{4}-(0[1-9]|1[0-2])$') e _validate_mes_ano (extraída para função própria por causa de TRY301) em src/tjro_juris/manifest.py, chamada dentro de ManifestJuris.load_text: uv run pytest -q tests/tjro_juris/test_juris_manifest.py tests/causaganha/decisoes/test_published.py -> 30 testes, 100% verde. Reprodução ao vivo pós-fix: discover_published_juris_datasets com o mesmo manifesto malicioso ('2024-01/../../secret-item') agora levanta ManifestFormatError('malformed row in ...: mes_ano must be YYYY-MM, got ...') antes de qualquer URL ser construída (capturado literalmente, não apenas inferido do teste). uv run pytest -q tests/tjro_juris/ tests/causaganha/decisoes/ tests/causaganha_mcp/test_decisoes_buscar.py -> 122 testes, 100% verde (nenhuma regressão nos consumidores diretos)."
---

# Evidência GREEN: `mes_ano` malformado agora é rejeitado no parse

`ManifestJuris.load_text` agora falha fechado (`ManifestFormatError`)
antes que qualquer `mes_ano` fora da forma `YYYY-MM` chegue perto de
`_juris_url`. Reprodução ao vivo do payload malicioso original confirma
que a mesma chamada que antes produzia uma URL com `../../` agora levanta
a exceção esperada. 30/30 testes dos arquivos tocados, 122/122 incluindo
os consumidores diretos (`decisoes_buscar`).
