---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-akb9oz-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
subject: "okf_knowledge"
reference: "docs/SECURITY_THREAT_MODEL.md Sec.3/5; knowledge/agent-runs/2026-09-25-exciting-mccarthy-r2xele/run.md (next_move); knowledge/agent-runs/2026-09-25-exciting-mccarthy-3zkmxg/run.md (next_move)"
finding: "docs/SECURITY_THREAT_MODEL.md Sec.5 (ordem de execucao) lista #1613 (CSP + piso XSS/runtime remoto) como item 7, apos #1608/#1609/#1610/#1611/#1615/#950/#1612 -- todos ja fechados ou com PR mesclada nesta e em rodadas anteriores, exceto a fatia nao-Go de #1609 (fora do controle desta sessao, decisoes de deploy). TM-08 (linha da matriz) descreve exatamente o gap: 'Nao ha CSP em Layout.astro' e pede corpus XSS + inventario de sinks {@html} + limite de origem para worker/dependencia remota (DuckDB-WASM). Os relatorios AgentRun de r2xele e 3zkmxg (2026-09-25, rodadas imediatamente anteriores) recomendam #1613 explicitamente como 'proximo alvo mais tratavel em TDD self-contained' -- ja e a 3a rodada seguida a apontar o mesmo proximo passo, entao selecionado como trabalho principal desta rodada em vez de reabrir #1610 (ja fechada de fato) ou tentar #1609/#1614 (infra de deploy/build, fora do controle de uma sessao sem credenciais)."
---

# Leitura: conhecimento OKF relevante

Leitura de `docs/SECURITY_THREAT_MODEL.md` (matriz operacional e ordem de
execucao) e dos `next_move` dos dois relatorios `AgentRun` mais recentes
(`r2xele`, `3zkmxg`), ambos de hoje. Os tres convergem no mesmo proximo
passo: `#1613` (CSP + piso de regressao XSS, TM-08), self-contained em
TypeScript/Astro, sem dependencia de credenciais externas ou decisoes de
infraestrutura de deploy -- selecionado como trabalho principal.
