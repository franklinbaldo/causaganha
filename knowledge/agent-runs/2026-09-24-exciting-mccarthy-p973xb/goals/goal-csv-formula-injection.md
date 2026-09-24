---
type: AgentGoal
id: "2026-09-24-exciting-mccarthy-p973xb-goal-csv-formula-injection"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
goal: "Neutralizar formula injection na exportacao CSV de web/src/components/PublicationSearch.svelte (issue #1612): toda celula cujo primeiro caractere significativo seja =, +, - ou @ deve ficar inerte ao abrir o CSV numa planilha, sem alterar a apresentacao normal na UI, o quoting RFC existente, o escopo/paginacao ou o nome do arquivo exportado."
rationale: "docs/SECURITY_THREAT_MODEL.md (mesclado nesta rodada como PR #1617) identifica TM-09: pub.texto e outros campos de publicacoes judiciais sao conteudo controlavel pela fonte e fluem sem neutralizacao para csvField() em PublicationSearch.svelte, que so escapa aspas/virgulas/quebras de linha (protege estrutura CSV, nao semantica de planilha). Um texto de publicacao comecando por '=', '+', '-' ou '@' e interpretado como formula por Excel/LibreOffice/Google Sheets ao abrir o arquivo exportado -- um vetor classico de CSV injection contra usuarios do CausaGanha. E trabalho real, bem-escopado, self-contained (nao depende de credenciais externas nem de nenhuma outra PR em voo), e o proprio corpo da issue #1612 ja define o gate automatizado esperado."
success_signal: "web/src/components/PublicationSearch.export.test.ts ganha casos novos para celulas comecando com =1+1, +SUM(A1:A9), -1+2, @cmd (e variantes com espaco/tab a frente) que afirmam que o texto exportado nao comeca mais com esses prefixos perigosos (fica prefixado com um caractere inerte, ex. apostrofo), enquanto strings benignas permanecem bit-a-bit identicas; o teste falha (RED) contra o csvField() atual antes da mudanca e passa (GREEN) depois; npm run test (vitest) do pacote web fica verde; nenhuma mudanca na apresentacao normal da tabela de resultados na UI (so o CSV exportado muda); npm run lint/typecheck do web continuam limpos."
status: "achieved"
---

# Objetivo: fechar TM-09 / issue #1612 (CSV formula injection)

Trabalho principal desta rodada, selecionado a partir do novo threat
model operacional mesclado nesta mesma rodada (`#1617`). Ver
`decision_ids`/`evidence_ids`/`check_ids` para o processo TDD
completo.
