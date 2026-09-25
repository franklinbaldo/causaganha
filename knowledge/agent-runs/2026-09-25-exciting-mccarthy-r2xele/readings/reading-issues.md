---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-r2xele-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, 27 abertas)"
finding: "Backlog de seguranca de docs/SECURITY_THREAT_MODEL.md: #1608/#1611/#1612/#1615/#1609(TM-02 Go)/parte-de-#1610 ja fechadas por rodadas anteriores/concorrentes nesta mesma janela (confirmado na leitura de PRs). Restam abertas: #1609 (relay Python + Cloudflare, ainda parcialmente aberta -- so o proxy Go foi fechado), #1610 (arquivo_ia_url: lado Python fechado por #1622, lado TypeScript -- web/src/lib/processoCnj.ts / DuckDBExplorer.svelte -- explicitamente listado como 'nao em escopo' no corpo de #1622, permanece aberto), #1613 (CSP + piso XSS), #1614 (supply chain Python/container), #1616 (contrato MCP de evidencia nao-confiavel). Demais issues abertas sao trilhas de longo prazo sem gate automatizado pronto para uma rodada unica: Parquet/CNJ (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985) bloqueadas por credenciais IA ausentes neste tipo de sessao (fato ja estabelecido por 9+ rodadas anteriores); segmenter (#1050/#1051/#1057/#1056/#1055/#1054/#1047/#1053/#884/#887/#886) sao rodadas de anotacao/treino continuas, ja com PR aberta (#1605); #950/#951/#1093 sao produto de longo prazo sem TDD gate imediato. #1610 (parte TypeScript) e o item mais tratavel: self-contained em web/src/lib/processoCnj.ts, sem credenciais externas, com precedente direto (a mesma politica ja implementada e testada no lado Python por causaganha.processos.service._validate_artifact_url em #1622, mesma issue)."
---

# Leitura: issues abertas

27 issues abertas revisadas via `list_issues` (owner=franklinbaldo,
repo=causaganha, state=OPEN). Backlog de seguranca operacional
(`docs/SECURITY_THREAT_MODEL.md`) e o mais tratavel por TDD em uma rodada
unica; `#1610` (validacao de URL de artefato de manifesto) tem sua metade
Python ja fechada por `#1622` e a metade TypeScript explicitamente
apontada como follow-up no corpo daquela PR -- selecionada como trabalho
principal desta rodada.
