---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-khpkk2-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Confirma o modelo mental do djen-backup (sync-manifest.parquet como fonte da verdade, djen_raw!=veredito de disponibilidade, 403 nunca e absent), o limite de tokens Panda/Svelte para o frontend, e as regras de estilo Python (ruff estrito, sem except Exception generico fora do bulkhead documentado na ADR 0011). Nenhuma mudanca de conteudo desde a ultima rodada que leu este arquivo (eb5f9r, 2026-09-24). Nao ha mencao a Wisk/AgentRun no CLAUDE.md em si -- essa politica de runtime vive em .claude/hourly-loop.md, um arquivo separado (ver reading-okf)."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Sem mudancas relevantes desde a
ultima rodada (`eb5f9r`): a arquitetura djen-backup, os contratos de
query do frontend, a fronteira de tokens CSS Panda/Svelte e as regras
de estilo Python permanecem como descritas. O arquivo nao entra em
nenhum conflito com o trabalho selecionado nesta rodada (ver
`goal_ids`), que e inteiramente sobre a linhagem `#1050`
(segmentador) e sobre desobstruir PRs de continuidade -- ambos ja
cobertos pelas secoes de estilo e "antes de commitar" do CLAUDE.md.
