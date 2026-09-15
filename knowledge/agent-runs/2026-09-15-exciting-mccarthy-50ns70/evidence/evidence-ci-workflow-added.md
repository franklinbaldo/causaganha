---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-50ns70-evidence-ci-workflow-added"
run_id: "2026-09-15-exciting-mccarthy-50ns70"
goal_id: "2026-09-15-exciting-mccarthy-50ns70-goal-cors-probe-ci"
kind: "diff"
reference: ".github/workflows/archive-cors-probe.yml"
summary: "Added a new scheduled workflow (cron '0 10 * * 1' + workflow_dispatch, permissions: contents: read), mirroring ia-practicality-probe.yml's shape: checkout, ./.github/actions/setup with dev=true (needed for the playwright dev dependency), `uv run playwright install --with-deps chromium`, then `uv run python -m scripts.benchmarks.archive_cors_probe`, with a GITHUB_STEP_SUMMARY table on completion. This is the CI wiring issue #1482's own 'Suggested next step' #3 asked for and PR #1489 explicitly deferred; it was blocked until this round's fix to the probe's playwright dependency resolution (see decision-python-over-node-playwright)."
---

# Evidência: workflow de CI adicionado

`.github/workflows/archive-cors-probe.yml`, agendado semanalmente + `workflow_dispatch`, no mesmo formato de `ia-practicality-probe.yml`. Fecha o item de follow-up explícito da issue #1482.
