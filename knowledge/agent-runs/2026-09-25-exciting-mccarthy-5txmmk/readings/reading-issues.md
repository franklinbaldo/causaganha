---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-5txmmk-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
subject: "open_issues"
reference: "https://github.com/franklinbaldo/causaganha/issues?q=is%3Aissue+is%3Aopen"
finding: "21 issues abertas. #1652 (security(archive): IA discovery must never trust an unauthenticated global search as canonical, criada 2026-09-25T19:28) tem checklist com 3 superficies: (1) generate_catalog.py, ja corrigida em rodada anterior a esta sessao; (2) reconcile_processos.py::_discover_juris_items, ja corrigida e mesclada via PR #1657 (allowlist de anos a partir do manifesto do proprio projeto); (3) reconcile_processos.py fallback JURIS/DataJud -- 'verificacao de digest (SHA-256) de arquivos remotos contra um manifesto de fontes confiaveis antes de trata-los como canonicos' -- ainda ABERTA, com uma PR externa (#1645, bot codex) proposta mas nao adotavel (ver reading-prs). Selecionada como trabalho desta rodada. Restante das 21 issues sao os blocos ja recorrentes e reconfirmados bloqueados por 5+ rodadas anteriores sem fato novo: Parquet/CNJ #1470/#1469/#1471/#1472/#1468/#1022/#985 (credenciais IA ausentes neste tipo de sessao) e segmenter #1050/#1051/#1057/#1056/#1055/#1054/#1047/#1053/#884/#887/#886 (ciclo de anotacao/treino continuo, PR #1605 bloqueada por conflito de merge em branch alheia sem permissao de push). #951/#1093 sao issues de produto (web) sem trabalho em andamento identificado nesta leitura, nao selecionadas por nao terem success_signal tao concreto quanto #1652 item 3."
---

# Leitura: issues abertas

Listagem completa das 21 issues abertas via GitHub MCP
(`list_issues`, `state=OPEN`, ordenado por `updated_at desc`). Corpo
completo lido para #1652 (issue mais recente, criada nesta mesma data,
com checklist granular por superfície de ataque). As demais issues
seguem blocos já documentados por rodadas anteriores (Parquet/CNJ
bloqueado por credenciais, segmenter em ciclo contínuo com PR #1605
bloqueada).
