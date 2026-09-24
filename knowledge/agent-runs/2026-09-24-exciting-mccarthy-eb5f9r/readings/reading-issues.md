---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-eb5f9r-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
subject: "open_issues"
reference: "mcp__github__list_issues (owner=franklinbaldo, repo=causaganha, state=open); mcp__github__issue_read #1050"
finding: "22 issues abertas. #1050 (corpus real do segmentador, RFC 0012) segue aberta: apos PR #1594/#1595 (mescladas por wisk(run) em 2026-09-20, fora do fluxo AgentRun), document_count=191/annotation_count=244/val_ceiling=test_ceiling=29 -- ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30 val e >=30 test). #1468-#1472 (cluster Parquet/CNJ) seguem bloqueadas por credenciais IA ausentes (handoff Wisk reconfirma isso pela 11a+ rodada consecutiva). #1482 (CORS) teve o item de confirmacao real-browser resolvido via PR #1489; itens restantes nao sao o foco desta rodada. Nenhuma issue nova fora do historico previamente registrado."
---

# Leitura: issues abertas

`mcp__github__list_issues` (state=open) retornou 22 issues. As
relevantes para a continuidade desta linhagem de rodadas:

- **#1050** -- corpus real multi-tribunal para o segmentador (RFC 0012).
  Ainda aberta. Estado ao vivo confirmado (ver reading-prs e checks
  desta rodada): `document_count=191`, `annotation_count=244`,
  `val_ceiling=test_ceiling=29` apos os lotes 24/25 (#1590, #1594)
  mesclados. RFC 0012 Sec 5 item 4 exige >=30 documentos em cada split
  val/test -- faltam ~1-2 lotes deste tamanho no ritmo atual.
- **#1468-#1472** -- cluster Parquet/CNJ (reordenacao, catalogo,
  regeneracao). #1470 (auditoria de catalogo) foi refrescada em
  2026-09-20 (0 perdas, 61 arquivos). #1471 (piloto TJRO 2026) segue
  bloqueada: nenhuma credencial IA de escrita disponivel via nenhuma
  fonte suportada (confirmado ao vivo contra `get_ia_s3_auth()`),
  handoff Wisk `handoffs/handoff-issue-1471-ia-publish-pending` marca
  isso como a 11a+ rodada consecutiva a reconfirmar o mesmo bloqueio.
  Nao acionavel por codigo puro nesta rodada tambem.
- **#1482** -- CORS no endpoint de download do archive.org. O item de
  confirmacao real-browser ja foi resolvido (PR #1489,
  `docs/planning/evidence/archive-cors-probe-real-browser.json`); nao
  e o foco desta rodada.
- Demais issues (#884, #886-887, #950-951, #985, #1022, #1051,
  #1053-1057, #1093, ...) sao continuidade de trabalho de dados/
  segmentador mais antigo, sem sinal de bloqueio novo ou urgencia
  superior ao estado atual das PRs abertas (ver reading-prs).

Nenhuma issue nova relevante fora do que as rodadas anteriores ja
mapearam.
