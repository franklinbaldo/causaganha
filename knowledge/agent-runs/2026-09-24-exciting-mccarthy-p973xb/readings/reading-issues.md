---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-p973xb-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
subject: "open_issues"
reference: "franklinbaldo/causaganha issues (list_issues, state=OPEN, 31 total, orderBy updated_at desc); issue_read #1612"
finding: "31 issues abertas. As 9 mais recentes (#1608-#1616, todas criadas/atualizadas as 19:16-19:17Z, minutos antes desta leitura) sao um novo backlog de seguranca gerado a partir de docs/SECURITY_THREAT_MODEL.md (PR #1617, ainda aberta -- ver reading-prs), cada uma com ameaca/invariante/gate automatizado explicitos. #1612 ('neutralizar formula injection na exportacao CSV') e bem escopada, self-contained (so web/src/components/PublicationSearch.svelte + o teste ja existente PublicationSearch.export.test.ts), nao depende de credenciais externas nem de #1617 estar mesclada, e tem gate automatizado explicito no proprio corpo da issue (expandir o teste com =1+1/+SUM/-1+2/@cmd/variantes com espaco). Selecionada como trabalho principal desta rodada. As 8 issues de Parquet/CNJ (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985) seguem bloqueadas por credenciais Internet Archive ausentes neste tipo de sessao -- fato ja reconfirmado por 8+ rodadas anteriores, nao reprovado ao vivo aqui por nao ter mudado. #1050 (corpus real do segmentador) segue como a linhagem ativa mais antiga, mas com dois PRs concorrentes em voo neste exato momento (#1605 dirty/conflito, #1607 clean -- ver reading-prs); nao selecionada como trabalho novo desta rodada para nao colidir com nenhuma das duas."
---

# Leitura: issues abertas

Releu a lista completa de issues abertas via `list_issues` (orderBy
`updated_at` desc, 31 no total) e leu integralmente `#1612` via
`issue_read`.

O achado central desta leitura: uma sessao concorrente publicou, ha
poucos minutos, um novo threat model operacional
(`docs/SECURITY_THREAT_MODEL.md`, PR `#1617`) que gerou 9 issues de
seguranca novas e concretas (`#1608`-`#1616`), cada uma com ameaca,
invariante e gate automatizado ja definidos no corpo. Isso muda o
proximo passo natural desta rodada: em vez de competir pela linhagem
`#1050` (que tem duas PRs concorrentes ja em voo, uma delas em
conflito), ha trabalho de dominio real, bem-escopado e imediatamente
acionavel em `#1612` (formula injection na exportacao CSV) --
self-contained, TDD-avel, sem dependencia de `#1617` mesclar
primeiro nem de credenciais externas.

As issues de Parquet/CNJ credenciadas permanecem bloqueadas sem
mudanca, reconfirmadas por 8+ rodadas anteriores nesta mesma janela
de trabalho.
