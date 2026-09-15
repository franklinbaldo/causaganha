---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-q4zn8q-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
subject: "open_issues"
reference: "mcp__github__list_issues (franklinbaldo/causaganha, state=OPEN) + issue_read em #1482 (corpo + comentário) via subagente de survey desta rodada"
finding: "#1482 (CORS do endpoint de download do archive.org bloqueando read_parquet() no navegador) tem a confirmação real-browser fechada (comentário de hoje 00:37 UTC, evidência commitada em docs/planning/evidence/archive-cors-probe-real-browser.json, workflow semanal .github/workflows/archive-cors-probe.yml) mas a correção sugerida no próprio corpo da issue (\"proxy pela origem do próprio dashboard\") permanece NAO implementada -- só a detecção/classificação (describeCorsBlockedDataset em DuckDBExplorer.svelte) existe. Nenhuma rodada anterior tentou o proxy; a rodada 50ns70 explicitamente fechou só o item de regressão em CI, deixando o item 2 (workaround) como follow-up separado. Cluster #1468-1472 confirmado esgotado no que não depende de IA_ACCESS_KEY/IA_SECRET_KEY (inalterado desde 11/09). #1051 (segmentador RFC 0012) segue sendo escalado por uma longa cadeia de rodadas hoje (review_count>=17 no início desta janela) -- não escolhido como foco desta rodada para evitar apenas repetir o mesmo padrão pela 13a+ vez, já que #1482 é um bug real de produção, sem bloqueio de credenciais, e ainda sem tentativa de correção."
---

# Leitura: issues abertas

## #1482 -- CORS do endpoint de download do archive.org (foco desta rodada)

Corpo da issue (autor franklinbaldo): `archive.org/download/{item}/{file}`
não envia `Access-Control-Allow-Origin`, enquanto `archive.org/metadata/...`
e `archive.org/advancedsearch.php` enviam. `DuckDBExplorer.svelte` roda
`read_parquet('https://archive.org/download/...')` via DuckDB-WASM/httpfs
diretamente no navegador -- um `fetch` cross-origin real, bloqueado pelo
spec CORS. Sugestão explícita do autor: "proxying through the dashboard's
own origin" (rejeitando full-download sem Range, que produziria resposta
opaca inútil para DuckDB-WASM).

Comentário único (mesmo autor, 00:37 UTC de hoje): confirmação real-browser
via Playwright/Chromium headless contra `archive.org` ao vivo -- endpoint de
metadata resolve com `type: "cors"`, endpoint de download falha com
`TypeError: Failed to fetch`. Evidência commitada em
`docs/planning/evidence/archive-cors-probe-real-browser.json`. Fecha o item
1 (confirmação) da issue. O comentário afirma explicitamente que **a
correção (item 2, proxy) segue não implementada** -- só detecção/classificação
existe em produção hoje.

Estado local confirmado por leitura direta do código
(`web/src/components/DuckDBExplorer.svelte`): `describeCorsBlockedDataset()`
e `probeDownloadCorsAccess()` apenas classificam e comunicam o bloqueio ao
usuário (`datasetStatus = 'cors-blocked'`), desabilitando a UI -- não há
nenhuma tentativa de contornar o bloqueio.

## Cluster Parquet/CNJ (#1468 e subissues) -- esgotado no que não depende de IA

Confirmado pela linhagem de hoje (afj2il, f3feqb, ...): todos os critérios
de aceite que não exigem publicação real no Internet Archive estão
fechados em código. #1472 e a metade final de #1471 seguem bloqueados por
`IA_ACCESS_KEY`/`IA_SECRET_KEY` ausentes -- não reverificado ao vivo nesta
rodada por já ter sido confirmado poucas horas antes (afj2il, mesma
manhã); nenhuma mudança de infraestrutura seria esperada nesse intervalo.

## #1051 -- segmentador RFC 0012

Cadeia longa de rodadas hoje (2cjjig, b3xdwp, f3feqb, afj2il, ...) escalou
`review_count` progressivamente rumo à meta de ~60 do RFC 0012 §5.4. Pool
de documentos pendentes e mecanismo (`annotate_second_independent.py` +
`adjudicate_segmenter_review.py`) já validados repetidamente. Deixado de
fora do foco desta rodada por já ter dezenas de rodadas dedicadas hoje --
prioridade dada a #1482, que é bug de produção real, desbloqueado e ainda
sem nenhuma tentativa de correção.

## Ruído descartado

PR #1353 (dependabot, `deployment/relay-cf`): aberta, verde, sem relação
com trabalho de domínio -- mesmo padrão de toda rodada anterior.
