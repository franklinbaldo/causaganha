---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-3zkmxg-evidence-green-zip-budgets"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
kind: "test_green"
reference: "tests/consolidate/test_zip_processor.py (14 testes: 7 pre-existentes + 7 novos); src/causaganha/consolidate/zip_processor.py"
summary: "Apos implementar ZipBudgetExceededError/DownloadTooLargeError, as constantes MAX_ZIP_MEMBERS/MAX_MEMBER_COMPRESSED_BYTES/MAX_MEMBER_UNCOMPRESSED_BYTES/MAX_COMPRESSION_RATIO/MAX_TOTAL_UNCOMPRESSED_BYTES/MAX_DOWNLOAD_BYTES, _is_safe_member_name/_check_member_budget/_safe_basename, e o parametro max_bytes em download_zip, os 14 testes do modulo passam. Os 7 testes pre-existentes (shapes de JSON, arquivos nao-JSON, JSON malformado, ZIP corrompido, multiplos arquivos) continuam verdes sem alteracao -- os orcamentos padrao nao afetam ZIPs legitimos do tamanho tipico do DJEN. process_zip_entry foi atualizado para sanitizar filename/tribunal via _safe_basename antes de compor paths temporarios, e para capturar DownloadTooLargeError (junto com httpx.HTTPError/RequestError ja existentes) e ZipBudgetExceededError (junto com OSError ja existente), logando eventos especificos (unsafe_zip_entry_metadata, zip_budget_exceeded) e limpando arquivos parciais antes de retornar (0, 0) -- o mesmo padrao de falha explicita e observavel ja usado pelas outras falhas desta funcao (download_failed, ndjson_write_failed)."
---

# Evidencia: GREEN apos implementar orcamentos de ZIP (#1611)

```
$ uv run pytest -q tests/consolidate/test_zip_processor.py
..............                                                           [100%]
14 passed
```

```
$ uv run pytest -q tests/consolidate/
......................................                                   [100%]
38 passed
```

Os 7 testes novos cobrem exatamente o gate automatizado pedido pelo corpo
da issue #1611: many-members bomb, membro acima do orcamento declarado,
alta razao de compressao, path traversal em nome de membro, ZIP normal
inalterado pelos orcamentos padrao, download acima do teto (aborta e apaga
o arquivo parcial) e download dentro do teto (aceito normalmente).
