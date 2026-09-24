---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-e3tk18-reading-issues"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
subject: "open_issues"
reference: "franklinbaldo/causaganha issues (list_issues, state=OPEN, 22 total, orderBy updated_at desc); issue_read #1256, #1050"
finding: "22 issues abertas, sem mudanca na lista desde a rodada i23hxr desta mesma janela. As 8 de Parquet/CNJ (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985) seguem bloqueadas por credenciais Internet Archive ausentes neste tipo de sessao -- fato ja reconfirmado por 7+ rodadas anteriores, nao reprovado ao vivo aqui por nao ter mudado. #1050 (corpus real do segmentador, RFC 0012) e a linhagem ativa: document_count=193/annotation_count=250 apos o merge de #1606 (reparo semantico da rodada i23hxr), val/test ceiling ainda 29/29 (< piso RFC 0012 Sec5 item4 de >=30/>=30). #1256 (fechada 2026-09-07, state_reason=completed, label needs-franklin, autor=OWNER franklinbaldo) permanece a mesma decisao formal ja descoberta por rodadas anteriores (eb5f9r em diante): 'o CausaGanha deve usar exclusivamente o WikiSkill como runtime do ciclo continuo... Novas rodadas nao devem criar AgentRun'. Sem fato novo desde a ultima verificacao: uv run wisk start reconfirmado ao vivo nesta rodada como blocked/no-eligible-session (identico a todas as rodadas anteriores desta janela), apesar de o git log de origin/main mostrar commits reais 'wisk(run):' intercalados com PRs de AgentRun ao longo do dia -- ou seja, o Wisk claramente executa em OUTRAS janelas/sessoes concorrentes, mas nao nesta. Nao ha fato novo que justifique reescalar a tensao AgentRun-vs-Wisk (ja escalada por multiplas rodadas anteriores sem resposta adicional do dono)."
---

# Leitura: issues abertas

Releu a lista completa de issues abertas via `list_issues` (nenhuma
mudanca desde `i23hxr` nesta mesma janela) e reconfirmou #1256 e #1050
via `issue_read`. As issues de Parquet/CNJ credenciadas permanecem
bloqueadas sem mudanca.

O achado relevante permanece de governanca: #1256 formaliza a
aposentadoria do AgentRun em favor do Wisk, mas nesta janela de
execucao especifica `uv run wisk start` continua retornando
`blocked: no-eligible-session`, mesmo com evidencia concreta (git log
de `origin/main`) de que o Wisk executou rodadas reais em outras
janelas hoje (batches 25, closeouts, etc). Isso e consistente com o
estado ja registrado por rodadas anteriores, nao um fato novo -- nao
reescala.
