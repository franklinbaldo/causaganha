---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-95dnzq-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. CLAUDE.md norma djen-backup (sync-manifest.parquet como fonte da verdade, djen_raw como codigo de transporte HTTP nunca veredito de disponibilidade, 403 nunca e absent), contratos de query (.qmd) e a fronteira Panda/Svelte -- nenhuma dessas areas de dominio e tocada diretamente pelo trabalho desta rodada (deployment/djen_proxy.go, .github/workflows/test.yml, deployment/DEPLOY_DJEN_V4.sh, web/src/lib/djenClient.ts). O trabalho selecionado toca a superficie de rede que alimenta djen-backup em producao (djen_proxy.go fica na frente de comunicaapi.pje.jus.br, a origem real de dados que djen.py consome), entao o invariante de 'ausencia nunca e erro de transporte' e relevante indiretamente: o proxy deve continuar deixando passar exatamente os GETs que djen.py.get_caderno_url/download_zip fazem, sem alterar nenhum codigo de status que o classificador de djen_status ja trata. A secao 'Antes de committing' (ruff check, ruff format --check, pytest -q) foi seguida integralmente; regras de estilo Python (TRY300/TRY301/TRY401, sem except Exception generico fora do bulkhead da ADR 0011) nao se aplicam ao codigo Go tocado, mas nenhuma delas foi violada nos arquivos Python nao tocados."
---

# Leitura: CLAUDE.md

Leitura integral do guia do projeto, conforme exigido pelo contrato
`AgentRun`. Nenhuma area de dominio normada por este arquivo (sync
engine djen-backup, contratos de query, fronteira CSS Panda/Svelte) e
alterada diretamente por esta rodada -- o trabalho fica em
`deployment/` (proxy Go, script de deploy), CI e um comentario em
`web/src/lib/djenClient.ts`. A relacao indireta relevante e que
`deployment/djen_proxy.go` fica na frente do endpoint real
(`comunicaapi.pje.jus.br`) que `src/djen_backup/djen.py` consome, entao
qualquer mudanca de allowlist precisa continuar deixando passar
exatamente o trafego que o sync engine real usa.
