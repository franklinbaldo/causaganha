---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-q4zn8q-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Confere com toda a linhagem de rodadas de hoje: guia cobre backend Python (src/causaganha, src/djen_backup), motor djen-backup (ADR 0012, sync-manifest.parquet como fonte de verdade), contratos de query .qmd, fronteira CSS Panda vs. bridge de compatibilidade em web/src/index.css, e regras de estilo (ruff estrito, sem except Exception amplo salvo bulkhead ADR 0011, TRY300/301/401, pre-commit = ruff check + ruff format --check + pytest -q). Nenhuma seção trata do frontend web/ além da fronteira CSS -- não há regra explícita sobre Cloudflare Workers em deployment/, mas o padrão já estabelecido em deployment/relay-cf/ (allowlist de host, streaming de corpo, testes vitest) é o precedente relevante para qualquer novo Worker desta rodada."
---

# Leitura: CLAUDE.md

Lido integralmente (system-reminder desta sessão traz o conteúdo completo).
Nada mudou em relação às leituras anteriores da linhagem de hoje. Pontos
relevantes para o trabalho desta rodada (proxy CORS para archive.org):

- O guia não define regras específicas para `deployment/*-cf/` (Cloudflare
  Workers), mas `deployment/relay-cf/` já estabelece um padrão real no
  repositório: Worker minimalista, allowlist explícita de host/caminho,
  streaming do corpo da resposta, testes Vitest com `fetch` mockado, sem
  `boto3` nem dependências pesadas.
- Regras de estilo Python (ruff estrito, sem `except Exception` amplo fora
  do bulkhead do ADR 0011) não se aplicam diretamente a `deployment/*-cf/`
  (JavaScript puro), mas seguem valendo para qualquer script Python tocado
  nesta rodada.
- `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`
  continuam sendo o piso de verificação antes de qualquer commit que toque
  Python; para o Worker/Svelte desta rodada, o equivalente é `npm test`
  dentro de `deployment/archive-cors-proxy/` e `web/`.
