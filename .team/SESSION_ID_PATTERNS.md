# Jules Session ID Patterns

## Overview

All PRs created by Jules contain a **session ID** that uniquely identifies the Jules session that created them. This session ID is embedded in the PR branch name and is used by the auto-fixer to send fix requests back to the originating session.

## Session ID Extraction Logic

The extraction logic (`_extract_session_id()` in `.team/repo/github.py`) supports multiple patterns:

### 1. **Numeric ID in Branch Name** (Primary Pattern - 100% of current PRs)

**Pattern:** `-(\d{15,})$`
**Location:** End of branch name
**Example Branch:** `sapper/refactor-repository-exceptions-14973691545505921838`
**Extracted ID:** `14973691545505921838`

**Usage:** All current Jules PRs (28/28) use this pattern.

### 2. **UUID in Branch Name** (Supported but not currently used)

**Pattern:** `([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$`
**Location:** End of branch name
**Example Branch:** `feature/fix-123-550e8400-e29b-41d4-a716-446655440000`
**Extracted ID:** `550e8400-e29b-41d4-a716-446655440000`

**Usage:** 0 PRs currently use this pattern (but it's supported).

### 3. **Jules URL in PR Body** (Fallback)

**Pattern:** `jules\.google\.com/task/(\d+)`
**Location:** PR body/description
**Example:** `View task at https://jules.google.com/task/123456789`
**Extracted ID:** `123456789`

**Usage:** 0 PRs currently rely on this (all have IDs in branch names).

### 4. **Generic Task/Session URLs** (Additional Fallback)

**Patterns:**
- `/task/([a-zA-Z0-9-]+)`
- `/sessions/([a-zA-Z0-9-]+)`

**Location:** PR body/description
**Usage:** 0 PRs currently use these patterns.

## Auto-Fix Behavior

The auto-fixer (`auto_reply_to_jules()` in `.team/repo/auto_fix.py`) follows this logic:

```
1. Check if PR has CI failures or merge conflicts
   └─ If PR is healthy → Skip (return success)

2. Extract session_id from PR
   └─ If no session_id found → Skip with message
   └─ If session_id found → Send message to that session

3. NEVER create new sessions
```

### Why This Works

**✅ All Jules PRs have session IDs**
- Tested against 28 real Jules PRs: 100% success rate
- Session IDs are always embedded in branch names

**✅ Keeps context in original session**
- Fixes are requested in the same session that created the PR
- No session proliferation

**✅ Clear separation of concerns**
- Scheduler: Creates new sessions for scheduled work
- Auto-fixer: Only sends messages to existing sessions

## Testing

Run the test suite to validate session ID extraction:

```bash
# Basic test
python test_session_id_extraction.py

# Comprehensive test with pattern analysis
python test_auto_fix_comprehensive.py
```

**Expected result:** All Jules PRs should have extractable session IDs.

## Summary Statistics (as of 2025-12-28)

- **Total Jules PRs analyzed:** 28
- **PRs with extractable session IDs:** 28 (100%)
- **Primary pattern:** Numeric ID (15+ digits) in branch name
- **Fallback patterns needed:** 0

**Conclusion:** The session ID extraction logic is robust and handles all current Jules PRs correctly.
