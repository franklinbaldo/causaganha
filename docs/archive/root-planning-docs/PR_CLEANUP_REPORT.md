# PR Cleanup Report - January 24, 2026

## Summary

Reviewed and cleaned up all open PRs for CausaGanha. Reduced from 20+ open PRs to 0.

## PRs Closed

### Obsolete PRs (code already in main)
- **#221** - Fix pydantic-ai RunResult access - The fix was already applied in `src/causaganha/analysis/analyzer.py`

### Stale/Conflicting PRs
- **#254** - Local embeddings (13K+ additions, 62 files) - Too large, has conflicts, superseded by codebase evolution
- **#218** - Archive pipeline hardening - Has conflicts, archive workflow is working

### Duplicate Architecture Reviews
Closed in favor of #264:
- #259, #252, #243, #234, #223, #217, #210

### Stale PM Daily Briefs
Closed as historical/resolved:
- #258, #251, #233, #222, #216, #212, #242

### Redundant V2 Infrastructure PRs
Closed as V2 implementation is complete:
- #262, #260, #256, #241, #235, #224, #220, #215

## PR Merged

- **#264** - Architecture Report V2 - Valuable analysis of code/documentation mismatches

## Scraping Status

The scraping infrastructure is working correctly:
- **Cloudflare Worker** (`djen-scraper/cloudflare/worker/`) handles continuous data collection
- **v2_daily_collect** workflow runs daily and is mostly successful
- **archive-zips** workflow runs for archiving to Internet Archive

Recent workflow runs:
- 2026-01-24: success
- 2026-01-23: success
- 2026-01-22: success
- 2026-01-21: success
- 2026-01-20: failure (isolated)
- 2026-01-19 - 2026-01-15: all success

## CI Note

Current CI is failing on the `ruff` linting step (tool not properly installed in workflow). This is unrelated to the PR cleanup and should be fixed separately.

---

*Report generated: 2026-01-24*
