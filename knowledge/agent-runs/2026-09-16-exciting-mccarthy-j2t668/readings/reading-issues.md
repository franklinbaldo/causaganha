---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-j2t668-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
subject: "open_issues"
reference: "github issues (list_issues, state=OPEN, franklinbaldo/causaganha), 22 total"
finding: "#1050 (segmenter: repair and scale the real training corpus) remains the most active lineage -- 14 real multi-tribunal batches already merged today (some via the AgentRun scaffold, some via a separate Wisk runtime), document_count at 126 confirmed live via scripts/segmenter_governance_status.py, val/test ceiling at 19/19 against RFC 0012 Sec 5 item 4's >=30/>=30 floor. #1051 (independent validation set) stays structurally blocked until #1050 raises the ceiling. #1468-#1472 (Parquet/CNJ chain) is a separate Wisk-driven lineage; #1471 has been credential-blocked (missing IA_ACCESS_KEY/IA_SECRET_KEY) for many rounds, outside this session's control. #1482 (CORS on archive.org for DuckDBExplorer) is open and undertouched, a candidate for a future dedicated round."
---

# Leitura: issues abertas

`mcp__github__list_issues` (owner=franklinbaldo, repo=causaganha,
state=OPEN, orderBy=UPDATED_AT desc) retornou 22 issues. Mais relevantes:

- **#1050** ("segmenter: repair and scale the real training corpus with
  agent annotation") -- linhagem mais ativa do repositorio hoje. 14 lotes
  reais ja mesclados (PRs #1539 ate #1567/8ef6637), alternando entre o
  scaffold AgentRun e um runtime paralelo chamado "Wisk" na mesma
  linhagem, sem sobreposicao de conteudo (cada rodada verifica o estado
  ao vivo antes de selecionar candidatos). `document_count=126`,
  `val_ceiling=test_ceiling=19` (confirmado ao vivo nesta rodada via
  `scripts/segmenter_governance_status.py`), ainda abaixo do piso
  RFC 0012 Sec 5 item 4 (>=30 val, >=30 test).
- **#1051** ("segmenter: build an independently annotated validation
  set") -- bloqueada estruturalmente: adjudicar mais do pool atual nao
  cruza o teto matematico enquanto #1050 nao crescer o corpus total
  (fato ja confirmado ao vivo por multiplas rodadas anteriores).
- **#1468-#1472** (cadeia Parquet/CNJ) -- linhagem Wisk paralela;
  #1471 bloqueada ha muitas rodadas por falta de credenciais IA, fora do
  controle desta sessao.
- **#1482** (CORS em archive.org para `DuckDBExplorer.read_parquet()`)
  -- aberta desde 2026-09-15, sem rodada dedicada ainda; candidata a
  trabalho futuro caso a linhagem #1050 sature ou bloqueie.
- Havia tambem uma PR aberta duplicada, #1568 ("fourteenth real
  multi-tribunal batch"), cujo conteudo ja estava integralmente mesclado
  em `main` por #1567 (mesmos 3 hashes de documento, mesmo teste de
  regressao) -- fechada nesta rodada como parte da leitura de
  continuidade (ver AgentDecision correspondente).

Nenhuma issue aberta hoje sugere abandonar a linhagem #1050; ao
contrario, o volume de rodadas consecutivas bem-sucedidas e o proprio
sinal de continuidade mais forte disponivel.
