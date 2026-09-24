---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
subject: "open_issues"
reference: "franklinbaldo/causaganha issues (list_issues, state=OPEN, 30 total apos #1615 fechar via #1619); issue_read #1608"
finding: "30 issues abertas (uma a menos que a leitura da rodada anterior p973xb, porque #1615 foi mesclada nesta mesma rodada via PR #1619 -- ver reading-prs). Do backlog de seguranca gerado por docs/SECURITY_THREAT_MODEL.md (#1608-#1616 mais #950 reaproveitada), #1612 e #1615 ja estao fechadas (mescladas em rodadas anteriores desta janela e nesta rodada, respectivamente). #1608 ('security(ci): eliminar eval em workflow_dispatch com secrets', TM-01, severidade Alta) e o proximo item na ordem de execucao explicita da Sec5 do threat model, permanece aberta, sem PR associada (closed_by_pull_requests.total_count=0) e bem escopada: .github/workflows/tjro-sync.yml usa uma string CMD construida a partir de tjro_ano/tjro_mes/tjro_desde_ano/tjro_tipos (workflow_dispatch.inputs) interpolados diretamente no corpo do script (${{ inputs.X }}) e depois reinterpretados via 'eval \"$CMD\"', num job com IA_ACCESS_KEY/IA_SECRET_KEY/RELAY_TOKEN no ambiente -- confirmado ao vivo nesta rodada como genuinamente explorável (ver decision-select-1608 e evidence-red-workflow-injection-demo): um valor malicioso de tjro_mes contendo ponto-e-virgula e um comando de shell executa esse comando no runner antes mesmo de 'eval' rodar, porque a substituicao ${{ }} acontece como texto literal antes do bash processar o script -- a mesma classe de vulnerabilidade (GitHub Actions script/template injection), nao apenas o 'eval' isolado citado no titulo da issue. O proprio corpo da issue pede explicitamente para auditar os demais workflows que montam comandos a partir de workflow_dispatch.inputs; essa auditoria (grep em todos os .github/workflows/*.yml) encontrou o mesmo padrao eval+CMD em .github/workflows/datajud-enrich.yml e o mesmo padrao de interpolacao insegura sem eval (mas igualmente explorável via GHA script injection) em bootstrap-corpus.yml e collect-zips.yml (ambos com secrets IA_ACCESS_KEY/IA_SECRET_KEY no job) e em roundtrip-check.yml/sample-segmenter-texts.yml (sem secrets no job, mas ainda executando codigo interpolado no runner). Selecionada como trabalho principal desta rodada. As issues de Parquet/CNJ credenciadas (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985) seguem bloqueadas por credenciais Internet Archive ausentes neste tipo de sessao -- fato ja reconfirmado por 8+ rodadas anteriores nesta mesma janela, nao reprovado ao vivo aqui por nao ter mudado."
---

# Leitura: issues abertas

Releu a lista de issues abertas via `list_issues` (30 apos o merge de
`#1619`/`#1615` no inicio desta rodada) e leu integralmente `#1608`
via `issue_read`.

`#1608` e o proximo item explicito na ordem de execucao do threat
model (`docs/SECURITY_THREAT_MODEL.md` Sec5, item 1): remover `eval`
do caminho secret-bearing de `.github/workflows/tjro-sync.yml`. Uma
demonstracao ao vivo nesta rodada (ver `evidence-red-workflow-injection-demo`)
confirmou que a vulnerabilidade real e mais ampla que apenas o `eval`
isolado: a interpolacao direta `${{ inputs.X }}` no corpo do script
`run:` ja e, por si so, uma injecao de codigo (GitHub Actions
script/template injection) — o `eval` reinterpreta a string resultante
uma segunda vez, mas a primeira injecao ja acontece antes disso. A
propria issue pede para auditar os demais workflows com o mesmo
padrao; essa auditoria encontrou mais 5 arquivos com a mesma classe de
problema (2 com `eval` explicito, 3 com interpolacao direta sem
`eval`), 2 deles carregando as mesmas credenciais de Internet Archive.

As issues de Parquet/CNJ credenciadas permanecem bloqueadas sem
mudanca, reconfirmadas por 8+ rodadas anteriores.
