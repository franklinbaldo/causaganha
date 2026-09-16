---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-hv2ep2-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
subject: "open_issues"
reference: "list_issues(state=OPEN), franklinbaldo/causaganha, 2026-09-16"
finding: "22 open issues, matching the pre-session summary. Dominated by the segmenter epic: #1050 (this round's target, unblocked/active), #1051 (validation-set adjudication, correctly parked -- its ceiling is a function of #1050's corpus size, per c4y4rc's diagnosis), #1047/#1053-1057/#1093 (GPU/deploy-blocked, out of scope), #884/#886/#887 (locked-holdout work, out of scope). The Parquet/CNJ epic (#1468-1472) is still open and untouched by this round -- did not re-verify IA_ACCESS_KEY/IA_SECRET_KEY env vars since this round never touches that epic and the prompt's own instruction was to leave it alone regardless. No new issue needed opening or closing this round."
---

# Leitura: issues abertas

`list_issues(state=OPEN)` confirmou 22 issues abertas, batendo com o
resumo pré-sessão. Nenhuma ação sobre issues fora de #1050 foi necessária
nesta rodada — #1051 permanece corretamente estacionada (seu teto de
val/test é função do tamanho do corpus de #1050, diagnosticado na rodada
c4y4rc), e a epic Parquet/CNJ (#1468-1472) segue esgotada sem
credenciais de Internet Archive, fora do escopo desta rodada.
