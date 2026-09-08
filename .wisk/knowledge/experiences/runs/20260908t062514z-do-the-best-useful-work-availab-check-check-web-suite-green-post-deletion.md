---
type: "RunCheck"
id: "run-checks/20260908t062514z-do-the-best-useful-work-availab/check-web-suite-green-post-deletion"
run: "runs/20260908T062514Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "npm test; npm run typecheck; npm run lint; uv run python scripts/render_queries.py && npm run build (all in web/, run both before and after deleting web/src/components/TribunalCoverageGrid.astro)"
result: "Before: 66/66 test files, 493/493 tests, 0 typecheck errors, 0 lint errors, 120/120 pages built. After: identical -- 66/66 test files, 493/493 tests, 0 typecheck errors, 0 lint errors, 120/120 pages built. No regression from the deletion. Unrelated codegen drift produced by 'npm ci' pulling a newer orval version (djen-zod.gen.ts docstring/zod.int() diff) and regenerated OG SVGs was identified and reverted with 'git checkout' before staging, keeping the diff scoped to the single file deletion."
status: "pass"
evidence: "run-evidence/20260908t062514z-do-the-best-useful-work-availab/evidence-orphan-confirmed-and-removed"
goal: "run-goals/20260908t062514z-do-the-best-useful-work-availab/goal-delete-orphaned-tribunal-coverage-grid"
---

# RunCheck
