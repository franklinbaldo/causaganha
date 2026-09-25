---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-3zkmxg-goal-zip-ingestion-budgets"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
goal: "Impor orcamentos de recursos explicitos em src/causaganha/consolidate/zip_processor.py (issue #1611, TM-05) contra decompression bombs, downloads sem teto e nomes de membro que escapem o diretorio do arquivo, falhando de forma explicita e distinta de um dataset vazio."
rationale: "docs/SECURITY_THREAT_MODEL.md (TM-05) identifica que stream_zip_to_ndjson faz json.load() por membro sem limitar tamanho comprimido/descomprimido, numero de membros ou razao de compressao, e que download_zip transmite para disco sem teto de bytes -- uma fonte oficial comprometida, resposta malformada ou artefato adulterado pode exaurir RAM/disco do runner de CI. E trabalho self-contained (um unico modulo Python, sem credenciais externas, sem dependencia de outra PR em voo) com gate automatizado ja especificado no corpo da issue."
success_signal: "tests/consolidate/test_zip_processor.py ganha casos que RED-confirmam contra o codigo anterior e GREEN-confirmam apos a correcao: (1) ZIP com mais membros que MAX_ZIP_MEMBERS levanta ZipBudgetExceededError; (2) membro com tamanho descomprimido acima do orcamento levanta ZipBudgetExceededError antes de qualquer json.load(); (3) membro com razao de compressao acima do orcamento levanta ZipBudgetExceededError; (4) nome de membro com path traversal (../) levanta ZipBudgetExceededError; (5) um ZIP normal, do tamanho tipico do DJEN, continua processando sem ser afetado pelos orcamentos padrao; (6) download_zip aborta e apaga o arquivo parcial quando a resposta excede max_bytes (DownloadTooLargeError), e aceita normalmente uma resposta dentro do orcamento. uv run pytest -q tests/consolidate/ fica verde; uv run ruff check/format --check ficam limpos."
status: "achieved"
---

# Objetivo: orcamentos de ingestao contra bombas de descompressao (#1611 / TM-05)

Trabalho principal desta rodada, selecionado a partir do backlog de
seguranca operacional (`docs/SECURITY_THREAT_MODEL.md`) apos confirmar
que `#1608`/`#1612`/`#1615` ja haviam sido fechadas por rodadas
anteriores/concorrentes na mesma janela. Ver `decision_ids`/
`evidence_ids`/`check_ids` para o processo TDD completo.
