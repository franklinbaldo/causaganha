---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-3zkmxg-evidence-red-zip-budgets"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
kind: "test_red"
reference: "tests/consolidate/test_zip_processor.py (7 novos testes: bomb por contagem de membros, membro acima do orcamento, alta razao de compressao, path traversal, ZIP normal inalterado, download acima do orcamento, download dentro do orcamento)"
summary: "Os 7 testes novos foram escritos primeiro contra a API alvo (ZipBudgetExceededError, DownloadTooLargeError, download_zip(..., max_bytes=...)) que ainda nao existia em src/causaganha/consolidate/zip_processor.py. Rodar uv run pytest -q tests/consolidate/test_zip_processor.py antes de qualquer mudanca de producao falhou na propria coleta do modulo: ImportError: cannot import name 'DownloadTooLargeError' from 'causaganha.consolidate.zip_processor' -- confirma que nenhum dos orcamentos de recurso pedidos pela issue #1611 existia antes desta rodada (RED por ausencia total da funcionalidade, o caso mais forte de RED)."
---

# Evidencia: RED antes da implementacao de orcamentos de ZIP (#1611)

```
$ uv run pytest -q tests/consolidate/test_zip_processor.py
==================================== ERRORS ====================================
___________ ERROR collecting tests/consolidate/test_zip_processor.py ___________
ImportError while importing test module '.../tests/consolidate/test_zip_processor.py'.
tests/consolidate/test_zip_processor.py:15: in <module>
    from causaganha.consolidate.zip_processor import (
E   ImportError: cannot import name 'DownloadTooLargeError' from 'causaganha.consolidate.zip_processor'
=========================== short test summary info ============================
ERROR tests/consolidate/test_zip_processor.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

Confirma que os orcamentos de recurso descritos em TM-05/#1611 (contagem de
membros, tamanho por membro, razao de compressao, nome de membro seguro,
teto de download) nao existiam em nenhuma forma antes desta mudanca.
