---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-epgxv2-reading-issues"
run_id: "2026-09-17-exciting-mccarthy-epgxv2"
subject: "open_issues"
reference: "github issues (list_issues, state=OPEN, franklinbaldo/causaganha), 22 total"
finding: "#1050 (segmenter: repair and scale the real training corpus) segue a linhagem mais ativa: 15 lotes reais ja mesclados (mecanismos AgentRun e Wisk alternando), document_count=132 e val/test ceiling=20/20 na ultima verificacao registrada (round j2t668), ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30). #1051 (validacao independente) permanece bloqueada ate #1050 elevar o teto. Nenhuma issue aberta sugere abandonar #1050; #1482 (CORS em archive.org) segue como candidata de reserva caso a linhagem sature."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues. Mais relevantes:

- **#1050** ("segmenter: repair and scale the real training corpus with
  agent annotation") -- linhagem mais ativa do repositorio. 15 lotes reais
  ja mesclados (PRs ate #1570/7dcfd2b), alternando entre o scaffold
  AgentRun e o runtime Wisk na mesma linhagem, sem sobreposicao de
  conteudo. `document_count=132`, `val_ceiling=test_ceiling=20`
  (numeros registrados pela ultima rodada, j2t668 -- a ser reconfirmado
  ao vivo nesta rodada via `scripts/segmenter_governance_status.py` antes
  de selecionar candidatos), ainda abaixo do piso RFC 0012 Sec 5 item 4
  (>=30 val, >=30 test).
- **#1051** ("segmenter: build an independently annotated validation
  set") -- bloqueada estruturalmente ate #1050 crescer o corpus total
  (fato ja confirmado ao vivo por multiplas rodadas anteriores).
- **#1468-#1472** (cadeia Parquet/CNJ) -- linhagem Wisk paralela; #1471
  segue bloqueada por credenciais IA ausentes, fora do controle desta
  sessao.
- **#1482** (CORS em archive.org para `DuckDBExplorer.read_parquet()`)
  -- ainda aberta e sem rodada dedicada; candidata a trabalho futuro caso
  a linhagem #1050 sature ou bloqueie antes do fim desta rodada.

Nenhuma issue aberta hoje sugere abandonar a linhagem #1050; o volume de
rodadas consecutivas bem-sucedidas continua sendo o sinal de continuidade
mais forte disponivel, e nenhum outro item aberto tem tanto contexto
acumulado e caminho de execucao ja provado.
