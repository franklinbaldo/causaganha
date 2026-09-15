---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-afj2il-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
subject: "open_issues"
reference: "mcp__github__list_issues (franklinbaldo/causaganha, state=OPEN, orderBy=UPDATED_AT desc) + issue_read em #1051, #1468, #1469, #1470, #1471"
finding: "22 issues abertas. #1051 (validação independente do segmentador, RFC 0012) é a mais recentemente atualizada (08:56 de hoje) e a única frente de domínio real desbloqueada: >12 rodadas de hoje já escalaram review_count de um baseline pequeno até 17, meta RFC 0012 §5.4 ~60. O cluster Parquet/CNJ (#1468-1472) teve TODOS os critérios de aceite que não exigem publicação real no Internet Archive fechados nesta madrugada (comentários de #1469 e #1470 confirmam item 1 e item 2 do checklist de #1468 inteiramente resolvidos em código; #1471 já tem a comparação local, a medição de custo de consulta E a prova de leitura real contra archive.org para o arquivo antigo -- resta só o lado do arquivo candidato/reordenado, que exige publicar no IA). #1472 (execução da regeneração seletiva) e a metade final de #1471 seguem bloqueados por IA_ACCESS_KEY/IA_SECRET_KEY ausentes. #1482 (CORS do endpoint de download do archive.org) foi investigado ao vivo em rodadas anteriores e confirmado sem correção possível sem proxy dedicado (download_endpoint_cors_enabled=false, confirmado com curl, urllib E navegador real headless -- não é artefato do proxy MITM deste ambiente); dashboard classificando-o corretamente permanece a decisão vigente."
---

# Leitura: issues abertas

Revisão ao vivo via `mcp__github__list_issues` + `issue_read` em `franklinbaldo/causaganha`.

## Cluster Parquet/CNJ (#1468 e subissues) -- esgotado no que não depende de IA

- #1468 (epic): checklist item 1 ("Implementação compatível incorporada e validada") e item 2 ("Auditoria reproduzível com plano por arquivo") resolvidos em código, por comentários datados de hoje em #1469/#1470.
- #1469: todos os critérios fechados exceto os que dependem da publicação real (#1472).
- #1470: todos os critérios fechados exceto o passo operacional de reexecutar no rollout real.
- #1471: comparação local (PR #1478), custo de consulta DuckDB nativo+WASM (PR #1480) e prova de leitura real contra archive.org para o arquivo **antigo** (PR #1483) já feitas. Falta só a mesma prova para o arquivo **candidato/reordenado**, que só existe depois de publicado -- bloqueado por #1472.
- #1472: bloqueado por `IA_ACCESS_KEY`/`IA_SECRET_KEY` ausentes -- `env | grep -iE 'IA_|ARCHIVE'` confirmado vazio nesta rodada (mesmo resultado desde 11/09).

## #1482 -- CORS do endpoint de download

Investigado e fechado como "sem correção sem proxy dedicado": PR #1491 portou a prova de CORS para Python e ligou-a ao CI (`.github/workflows/archive-cors-probe.yml`), confirmando ao vivo que `archive.org/download/...` não envia `Access-Control-Allow-Origin` (metadata endpoint envia, download endpoint não), reproduzido em Chromium headless real. Não é um artefato do proxy MITM deste sandbox.

## #1051 -- única frente de domínio real desbloqueada

RFC 0012 exige ~60 ReviewRecords adjudicados (30 validação + 30 teste) antes do release v8 do segmentador. Linhagem de hoje (2cjjig, b3xdwp, f3feqb e outras) escalou review_count de um baseline menor até 17 usando o mesmo mecanismo validado: `scripts/annotate_second_independent.py` (segunda anotação por subagente Técnica 1 isolado, família de modelo distinta da anotação histórica) + `scripts/adjudicate_segmenter_review.py` (resolve divergências contra a guideline) + `store.write_review` (rejeita pares não-independentes via `NonIndependentReviewError`). f3feqb's next_move aponta 44 documentos pendentes (34 com exatamente 1 anotação capaz de independência, 10 com 2 anotações mas nenhum par independente).

## Ruído descartado

PR #1353 (dependabot, deployment/relay-cf): stale desde 09/09, sem relação com trabalho de domínio -- mesmo padrão de toda rodada anterior, deixada de lado.
