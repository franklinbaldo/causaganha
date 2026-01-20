## 🧹 2025-12-24 - Atomic Commits
**Observation:** During a dead code removal task, I used `ruff --fix` which corrected several unrelated linting issues in other files.
**Action:** The code review flagged this as a violation of the "atomic commit" principle. I was instructed to revert the unrelated changes and resubmit a pull request that was focused only on the dead code removal. This reinforces the importance of keeping pull requests small and focused on a single logical change.
