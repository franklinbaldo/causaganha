---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-0iuk22-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
subject: "open_issues"
reference: "GitHub issues list (state=OPEN, 22 total, ordered by updated_at desc), #1050, #1051, #886, #887"
finding: "Top of the list by recent activity: #1050 (segmenter: repair and scale the real training corpus with agent annotation) and #1051 (segmenter: build an independently annotated validation set), both updated by the previous round (c4y4rc, merged as PR #1535/1e835c4), which redirected the lineage's next_move from #1051 (adjudicate within the fixed 61-doc pool) to #1050 (grow total corpus -- mathematically required to cross RFC 0012 Sec 5 item 4's >=30 val/>=30 test per-split floor). #1050's own body explicitly asks to 'mine real candidate documents for rare categories' and 'include multiple document templates/types and... multiple tribunals/sources' -- unchecked work items, never done: all 61 documents currently in the store are TJRO only (source.system in {tjro_juris, internet_archive_djen_ocr}). Separately, #886/#887 are a distinct, earlier-stage lineage (qualifying a single non-TJRO full-text source for the *locked final holdout*, #884) -- explicitly out of scope for #1050 ('This issue is about train supply. It must not consume the final locked holdout from #884'), so not conflated with this round's work. Other open issues (Parquet/CNJ epic #1468-1472, DuckDB CORS #1482, MCP endpoint #950/#951, etc.) are unrelated to the current lineage and were already triaged as blocked-on-credentials or lower priority by earlier rounds."
---

# Leitura: issues abertas

`list_issues` (state=OPEN) retornou 22 issues. As duas mais recentemente
atualizadas sao #1050 e #1051 -- ambas tocadas pela rodada anterior
(c4y4rc), que redirecionou o proximo passo real da linhagem para #1050
(crescer o corpus total), deixando `knowledge/backlog/issue-1050.md` como
`status: unblocked` com a instrucao explicita de minerar novos documentos
candidatos multi-tribunal. O corpo original de #1050 ja pede isso
("mine real candidate documents for rare categories", "include multiple
document templates/types and... multiple tribunals/sources") como itens de
trabalho nunca marcados. Verificado ao vivo nesta rodada
(`store.list_documents()`): os 61 documentos atuais sao 100% TJRO
(`source.system` em `{tjro_juris, internet_archive_djen_ocr}`), confirmando
que esse item segue genuinamente aberto.

#886/#887 sao uma linhagem irma, mas distinta: qualificam uma fonte
nao-TJRO para o **holdout final trancado** (#884), nao para o suprimento de
treino de #1050 -- o proprio corpo de #1050 exclui explicitamente
contaminar #884. Nao ha sobreposicao de escopo a resolver.

Demais issues abertas (epic Parquet/CNJ #1468-1472, CORS DuckDB #1482,
endpoints MCP #950/#951, datasets TCU/TSE #1022/#985, etc.) sao de outras
linhagens, ja triadas em rodadas anteriores (Parquet bloqueado por
IA_ACCESS_KEY/IA_SECRET_KEY ausentes) ou de prioridade menor frente ao
trabalho em andamento ha 10+ rodadas em #1050/#1051.
