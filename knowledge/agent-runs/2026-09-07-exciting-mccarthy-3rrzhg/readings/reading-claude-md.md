---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-3rrzhg-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-3rrzhg"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md still documents the djen-backup manifest architecture, the MCP query-contract flow, the CSS token boundary and 'before committing' checks (ruff check, ruff format --check, pytest -q). It does not mention WikiSkill, AgentRun, or the hourly-loop mechanism at all — the operational loop itself lives only in .claude/hourly-loop.md and .claude/agent-run-scaffold.md, both outside CLAUDE.md's scope. Nothing in CLAUDE.md is stale relative to the repository's current state: the manifest-source-of-truth migration it describes (Fases 0-3, sync-manifest.csv retired) matches docs/planning/manifest-source-of-truth.md's own 'Fase 3 (✅ 2026-07-08, PR #800)' status, confirmed independently this round by grepping .github/workflows/render-manifest-parquet.yml, which now reads 'sync-manifest.csv is retired as a source and no longer auto-exported here'."
---

# Reading: CLAUDE.md

No drift found between CLAUDE.md's architecture description and the live repository state. CLAUDE.md does not govern the hourly-loop mechanism itself (that is `.claude/hourly-loop.md` + `.claude/agent-run-scaffold.md`), which is the subject of open PR #1251 — see `reading-prs.md`.
