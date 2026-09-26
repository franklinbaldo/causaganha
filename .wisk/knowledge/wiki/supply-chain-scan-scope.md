---
type: "WikiEntry"
id: "wiki/supply-chain-scan-scope"
title: "Supply-chain scan scope: scan what ships, remove dead tools instead of suppressing findings"
status: "active"
tags: ["security", "supply-chain", "ci", "dependencies"]
---

# Supply-chain scan scope

## Summary

`#1614`/TM-10 needed a vulnerability scanner + SBOM gate wired into CI (the lock/digest/non-root slice had already closed via `#1635`). The closing round (PR `#1640`) established three reusable decisions for any future dependency-audit work in this repository.

**Scan the dependency set actually shipped, not the full dev environment.** `deployment/mcp/Dockerfile` installs via `uv sync --frozen --no-dev --no-editable`; the CI gate (`supply-chain` job in `.github/workflows/test.yml`) audits that exact set (`uv export --frozen --no-dev --no-hashes` piped into `pip-audit`), not the full dev environment `.github/actions/setup` installs for testing/linting/docs. This is not just narrower scope for its own sake — it is *more correct*: dev-only tooling (mkdocs-material, marimo, etc.) is never exposed to production or to any attacker-reachable surface, so a vulnerability in it is a different risk class than one in code the MCP container actually runs. Scanning the shipped set also means the gate doesn't need to carry accumulated `--ignore-vuln` exceptions for dev-only findings at all — the shipped set was clean (`pip-audit`: "No known vulnerabilities found", 109-component CycloneDX SBOM) with zero suppressions.

**Prefer removing a dead/unused tool to suppressing its vulnerability.** `safety` (a competing vulnerability scanner) was a declared dev dependency invoked by no script, test, or CI workflow in this repository (confirmed by grep across `src/`, `scripts/`, `tests/`, `.github/`). Its own transitive dependency `nltk` carried `PYSEC-2026-3740`, a vulnerability with no fix version published. Removing `safety` removed the vulnerability along with the dead weight, instead of adding an `--ignore-vuln` that would have to be re-justified every time someone re-read the scan output. This also collapsed `typer` out of the resolved environment entirely — it had survived only as `safety`'s own unrelated transitive dependency since RFC 0013's Cyclopts migration.

**A transitive pin from *other* dev-tooling can be an accepted, documented scope boundary — but only when it's genuinely out of the shipped surface.** `pymdown-extensions` (via `mkdocs-material`, the docs generator) has two known vulnerabilities fixed in `>=11.0.1`, but `marimo==0.23.14`'s own dependency metadata pins `pymdown-extensions<11`. Bumping `marimo` to unblock a doc-tooling library is an unrelated behavior change to the project's notebook tooling (`scripts/check_notebooks_synced.py` compares generated `.ipynb` output against `marimo`'s own export format — a version bump risks silent drift there), so it was left as documented, out-of-scope debt in `docs/SECURITY_THREAT_MODEL.md` TM-10 rather than forced into this PR. The same shape will recur: when dependency A pins dependency B below B's fix version, and A is dev-only/never-shipped, document the boundary explicitly instead of either suppressing the finding silently or dragging an unrelated upgrade into a security PR's diff.

## References

- `docs/SECURITY_THREAT_MODEL.md` TM-10
- `deployment/mcp/README.md` (SBOM + scan section)
- `tests/deployment/test_supply_chain_scan.py`
- [PR #1640](https://github.com/franklinbaldo/causaganha/pull/1640)
