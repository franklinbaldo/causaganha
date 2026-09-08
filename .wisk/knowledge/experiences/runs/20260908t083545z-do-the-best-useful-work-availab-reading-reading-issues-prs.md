---
type: "RunReading"
id: "run-readings/20260908t083545z-do-the-best-useful-work-availab/reading-issues-prs"
run: "runs/20260908T083545Z-do-the-best-useful-work-available-in-this-reposi"
kind: "repo-state"
subject: "GitHub issues/PRs survey via mcp__github tools"
reference: "https://github.com/franklinbaldo/causaganha/issues (17 open), pull_requests (0 open), actions runs on main"
finding: "17 open issues, 0 open PRs. All open issues are blocked on external creds (#950 remote MCP deploy needs GCP; #951/#1093 depend on #950) or are heavy segmenter ML/annotation research (#1047 roadmap #1050-#1057; locked-holdout #884/#886/#887). CI green on main (test.yml, okf.yml, deploy-web.yml, codeql all success on latest push). Baseline uv run pytest -q: all green (1 skipped); ruff check/format clean."
---

# RunReading
