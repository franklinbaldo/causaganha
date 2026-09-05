---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-ejibsp-evidence-index-md-crash-fix"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal_id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
kind: "runtime"
reference: "scripts/check_agent_run_completeness.py; knowledge/agent-runs/index.md"
summary: "Dogfooding the new directory-mode checker against the real knowledge/agent-runs/ tree — after adding knowledge/agent-runs/index.md (a plain, frontmatter-less doc, matching how knowledge/index.md is exempted from the OKF001 frontmatter check as 'reserved') — crashed with okf_parser.parser.DocumentParseError: 'concept must start with YAML frontmatter delimited by ---' instead of skipping the file, because main()'s directory scan called parse_document on every *.md file unconditionally. Fixed by catching DocumentParseError around the parse call and skipping the file when scanning a directory (still propagating the error for an explicit single-file argument, where a parse failure is a real usage error). Covered by test_main_over_a_directory_skips_frontmatter_less_index_files; uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs now exits 0 over the real tree instead of crashing."
---

# Evidência: crash real descoberto por dogfooding, e correção
