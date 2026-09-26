---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-uz8msx-reading-prs"
run_id: "2026-09-26-exciting-mccarthy-uz8msx"
subject: "open_prs"
reference: "GitHub PRs abertas (franklinbaldo/causaganha, mcp__github__list_pull_requests state=open, 5 abertas)"
finding: "#1653 (docs-only closeout da rodada r0zxiq, aberta 2026-09-25T19:28Z): 14/14 checks de CI verdes (incluindo GitGuardian e validate), mas mergeable_state='unknown' e get_status devolve total_count=0/state='pending' -- consistente com o relato de r0zxiq/orr2e3 de que duas tentativas de merge via API falharam com erro 405 citando 'Required status check GitGuardian Security Checks is expected', apesar do check run aparecer completed/success. Nenhum fix commit necessário, só reexecutar o merge. #1643/#1644/#1645 (3 PRs externas do bot codex, abertas 2026-09-25T15:09-15:10Z, atacando a mesma classe de #1652/TM-16): TODAS agora superadas -- #1652 foi fechada nesta janela por 3 PRs próprias já mescladas (item 1: rodada 230b86 direto em main; item 2: PR #1657/#discover_juris_items; item 3: PR #1659/_verify_artifact_identity), então #1643 (duplica o item 1, base sha 7dc8094 anterior ao fix real), #1644 (duplica o item 2, já fechado por #1657) e #1645 (duplica o item 3, já fechado por #1659) não têm mais trabalho útil a oferecer -- são ruído no board de PRs abertas para rodadas futuras. #1353 (dependabot, bump @vitest/mocker 4.1.10->4.1.11 em deployment/relay-cf, aberta 2026-09-09): 6/6 checks reportados verdes (CodeQL 'neutral' é normal para bump JS puro), mergeable_state='unknown' mas sem histórico de tentativa de merge -- rotina, nunca examinada por nenhuma rodada anterior."
---

# Leitura: PRs abertas
