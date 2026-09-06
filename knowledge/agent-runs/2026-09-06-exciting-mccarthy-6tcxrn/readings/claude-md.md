---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-6tcxrn-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-6tcxrn"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (untouched this round) and the web frontend in web/ (Astro 5 + Svelte 5), fed by .qmd query contracts. The CSS token boundary rule (Brazilian Modernism --s-*/--papel-*/--tinta-* vs. semantic --color-*/--space-*/--pico-* tokens) is the closest-matching invariant to this round's work, but neither lane applies any more: the repo has moved past Pico/legacy CSS entirely onto the Panda CSS + Cobogó preset foundation (confirmed live by installing web/ deps and reading node_modules/cobogo/preset/index.mjs), so CLAUDE.md's CSS-boundary section describes a foundation the #1169 reboot already replaced — a documentation-drift candidate for a future round, out of scope here. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`, plus (per this round's own scaffold) `uv run okf-parser check knowledge --relational-schema okf.schema.sql`. This round's selected work (removing an orphaned Astro component and adding a regression test) touches none of djen-backup's manifest/upload invariants."
---

# Leitura de CLAUDE.md

Nenhuma regra do motor djen-backup (manifesto, `djen_raw` vs `djen_status`, upload IA) é tocada nesta rodada — o trabalho é inteiramente em `web/`. A seção de fronteira CSS do próprio `CLAUDE.md` já está desatualizada frente ao reboot Cobogó/Panda (#1169): não há mais Pico nem tokens `--papel-*`/`--tinta-*` no shell atual, que agora usa exclusivamente tokens semânticos gerados pelo Panda via o preset `cobogo`. Registrado como achado para uma rodada futura de documentação, não perseguido aqui.
