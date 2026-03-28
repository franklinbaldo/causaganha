1. Modify `scripts/dev/check_pr_lint_status.py` to calculate PR age (how long it has been ready/core-green).
    - It should get the time the PR was created or last updated and calculate the age in hours compared to the current time.
    - It should determine an urgency bucket based on the age (`fresh` for < 12h, `warning` for 12-24h, `critical` for > 24h).
2. Update the output dictionary in `check_pr_lint_status.py` to include `ready_since_hours` and `urgency_bucket`.
3. Update `dashboard/src/pages/admin/perf.astro` to display the urgency bucket and age. We can add a badge for `fresh`, `warning` and `critical` statuses.
4. Add unit tests for the bucketing logic in `check_pr_lint_status.py`.
5. Pre-commit checks.
6. Submit PR.
