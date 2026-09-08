---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-k18r9l-adr-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-k18r9l-adr"
goal_id: "2026-09-08-exciting-mccarthy-k18r9l-adr-goal-except-exception-adr"
kind: "diff"
reference: "git diff (working tree, this round): docs/adr/0011-broad-except-in-worker-loop-bulkheads.md (new), CLAUDE.md (rule amended), src/djen_backup/archive.py:264, src/causaganha/analysis/llm_analyzer.py:387,499, src/causaganha/consolidate/cli.py:160 (one-line comment each), tests/test_except_exception_policy.py (new)"
summary: "docs/adr/0011 (new, ~90 lines, standard Nygard format) documents the context (4 sites, 3 prior rounds' non-decision, the BLE001 .exception() exemption confirmed by a minimal repro, per-site analysis of why narrowing would be worse), the decision (keep except Exception, cite the ADR at each site, amend CLAUDE.md, no ruff.toml change needed), and consequences. CLAUDE.md's 'No blind except Exception' bullet gained one sentence stating the bulkhead carve-out and citing the ADR. Each of the 4 call sites gained a trailing comment: `# per-item bulkhead, see docs/adr/0011` (archive.py), `# per-model bulkhead, see docs/adr/0011` and `# per-key/model bulkhead, see docs/adr/0011` (llm_analyzer.py's two sites), `# per-table bulkhead, see docs/adr/0011` (cli.py) -- no behavior change, comment-only. tests/test_except_exception_policy.py (new, ~45 lines) scans src/**/*.py for `except Exception` lines and asserts each cites 'docs/adr/0011' or is in a grandfathered ruff.toml per-file-ignore, so a future uncited broad catch fails CI."
---

# Evidence: diff

Resumo do diff desta rodada: ADR novo, regra do CLAUDE.md ajustada, 4 comentarios pontuais nos sites existentes (sem mudanca de comportamento), e um teste novo que aplica a politica de forma automatizada.
