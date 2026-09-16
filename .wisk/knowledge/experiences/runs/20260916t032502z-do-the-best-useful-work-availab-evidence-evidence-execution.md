---
type: "RunEvidence"
id: "run-evidence/20260916t032502z-do-the-best-useful-work-availab/evidence-execution"
run: "runs/20260916T032502Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_archive_cors_proxy_ci_coverage.py; .github/workflows/test.yml (new archive-cors-proxy job)"
summary: "RED: tests/test_archive_cors_proxy_ci_coverage.py's two assertions (npm test wired into CI, npm run check/wrangler dry-run wired into CI) failed against unmodified test.yml with an explicit AssertionError naming the missing coverage. GREEN: added an archive-cors-proxy job to .github/workflows/test.yml (checkout, setup-node@22, npm ci, npm test, npm run check) mirroring the existing 'web' job's shape; same two tests now pass (2 passed). Verified the new job's steps actually succeed standalone in this sandbox with zero Cloudflare credentials: 'npm test' -> 15 passed (deployment/archive-cors-proxy/test/index.test.js, @cloudflare/vitest-pool-workers local workerd sandbox); 'npx wrangler deploy --dry-run' -> bundles cleanly ('Total Upload: 3.32 KiB', '--dry-run: exiting now'), no auth prompt. Full repo suite green after the change: 'uv run pytest -q' exit 0 (full run, no failures); 'uv run ruff check' -> All checks passed; 'uv run ruff format --check' clean on the new test file; 'python -c import yaml; yaml.safe_load(...)' confirms test.yml stays valid YAML."
goal: "run-goals/20260916t032502z-do-the-best-useful-work-availab/goal-goal-task-advance"
---

# RunEvidence
