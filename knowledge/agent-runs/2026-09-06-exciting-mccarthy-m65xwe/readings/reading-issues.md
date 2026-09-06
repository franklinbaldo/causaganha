---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-m65xwe-reading-issues"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
subject: "open_issues"
reference: "17 open issues in franklinbaldo/causaganha as of 2026-09-06T11:32Z (mcp__github__list_issues, state=OPEN)"
finding: "Every one of the 17 open issues remains blocked or explicitly deprioritized, unchanged from every prior round's assessment (yigsua, 6x90uc): #1047/#1050/#1051/#1053/#1054/#1055/#1056/#1057/#884/#886/#887 need GPU/active-learning/annotation work unsuited to an unattended round; #1022/#1011/#985 need a live credentialed Internet Archive upload — verified this round that IAS3_ACCESS_KEY/IAS3_SECRET_KEY (the actual env vars src/causaganha/pipeline/ia_s3.py reads) are absent from this session's environment (only AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are set, unrelated — the project explicitly avoids boto3/AWS-style auth for IA per CLAUDE.md), so #1022 (marked 'READY para IMPLEMENTAÇÃO' with its prerequisite #1020 confirmed merged) still cannot be executed live in this session; #950/#951 need a live hosting/deploy decision; #1093 is explicitly marked 'NÃO é prioridade imediata' by its own owner. No open issue is actionable this round. Per CLAUDE.md's own instruction that issues are an opportunity queue, not a ceiling, this round looked past the issue tracker: it found via `npm run typecheck` in web/ that 19 pre-existing TypeScript errors exist (matching the count round yigsua's evidence already logged as 'pre-existing, no new ones') and, critically, that `npm run typecheck` is never invoked by any CI workflow (.github/workflows/test.yml's web job runs lint/test/build only) — so this class of type error has been silently accumulating with no gate."
---

# Leitura das issues abertas

Todas as 17 issues abertas seguem bloqueadas ou despriorizadas, exatamente como as rodadas anteriores (yigsua, 6x90uc) já haviam concluído — inclusive verificando ao vivo nesta rodada que as credenciais reais que #1022 precisaria (`IAS3_ACCESS_KEY`/`IAS3_SECRET_KEY`) não existem neste ambiente. Como a fila de issues não é o teto do que pode ser melhorado, esta rodada procurou fora dela e achou um gap real: `npm run typecheck` (astro check) nunca roda em CI e acumula 19 erros de tipo pré-existentes, todos em arquivos de teste do web/.
