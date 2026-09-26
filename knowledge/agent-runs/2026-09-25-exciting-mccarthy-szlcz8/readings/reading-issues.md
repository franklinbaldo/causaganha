---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-szlcz8-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-szlcz8"
subject: "open_issues"
reference: "GitHub issues abertas (franklinbaldo/causaganha, mcp__github__list_issues, 21 abertas)"
finding: "Issue mais recente e mais acionável: #1652 (2026-09-25T19:28Z, TM-16) 'IA discovery must never trust an unauthenticated global search as canonical' — abre uma nova linha na matriz de ameaças cobrindo 3 superfícies que faziam busca livre no namespace público do IA e tratavam o resultado como catálogo canônico, sem allowlist nem verificação de digest: (1) scripts/generate_catalog.py com --verified-inventory ainda caindo em list_ia_items() — CORRIGIDO nesta mesma rodada anterior (230b86), com regressão em tests/test_archive_partitions.py; (2) scripts/reconcile_processos.py::_discover_juris_items — aceita qualquer item IA que bata com o regex tjro-juris-{ano}, sem allowlist; diagnóstico já existe numa PR externa (codex #1644), mas desatualizada contra main e com o check 'lint' falhando; (3) mesmo arquivo, fallback JURIS/DataJud geral — sem verificação de digest SHA-256; diagnóstico externo (codex #1645) com CodeQL/tests falhando. Critério de conclusão da issue lista os 3 itens como checkboxes, com (1) já marcado. Resto do backlog de segurança (#1608/#1609/#1611/#1612/#1613/#1614/#1615/#1616) já fechado por ~13 rodadas OKF anteriores hoje, confirmado pela ausência na lista atual de issues abertas. Fora do cluster de segurança: clusters #1468-1472 (Parquet/CNJ) e #1022/#985/#951/#1093 seguem sem PR em voo, historicamente bloqueados por credenciais IA ausentes nesta sessão ou por decisão de escopo maior; cluster #1047-1057/#884/#886/#887 (segmenter RFC 0012) é a frente mais antiga, reconfirmada por dezenas de rodadas hoje/ontem, sem novidade nesta leitura."
---

# Leitura: issues abertas
