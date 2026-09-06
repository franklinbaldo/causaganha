---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-ucw90y-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (sync-manifest.parquet on IA is the sole source of truth; djen_raw is a transport code, never an availability verdict) and the web frontend fed by .qmd query contracts plus a CSS token boundary (Brazilian Modernism --s-*/--papel-*/--tinta-* confined to marketing pages; semantic --color-*/--space-* everywhere else). This round's selected work (adversarial review of PR #1169, the repo owner's web reboot) is a review-only task, no source files changed, so none of CLAUDE.md's correctness rules for djen-backup/manifest are engaged. The relevant guidance instead is procedural: 'Before committing: uv run ruff check / ruff format --check / pytest -q' (not applicable here since nothing was committed to the product tree) and the general engineering discipline of verifying claims against live code rather than trusting a PR description at face value — the same standard CLAUDE.md applies to the djen manifest ('do not assume a recorded status is right just because it looks canonical') was applied here to the PR's own claims about preserved contracts."
---

# Leitura de CLAUDE.md

Nenhuma regra de correção do manifesto DJEN ou upload IA se aplica ao trabalho desta rodada (revisão adversarial de uma PR de reboot visual, sem mudança de código de produto). O princípio que se aplica por analogia é o de não confiar em uma alegação sem verificação ao vivo — usado aqui para checar, via diff/grep reais, se a PR #1169 de fato preserva os contratos que alega preservar.
