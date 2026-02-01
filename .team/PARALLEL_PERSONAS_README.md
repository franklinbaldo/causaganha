# Parallel Personas Implementation - Documentation Package

> **Note (2026-01-29):** This is a historical planning document from 2026-01-11. The team now has **21 personas** (20 AI + 1 human), down from 23 at time of writing. Deleted personas: Typeguard, Sheriff, Simplifier, Organizer, Refactor. Added: Deps, Meta, Franklin. The mail system described here has been implemented. Persona prompts now use the **ROSAV framework** (Role, Objective, Situation, Act, Verify).

**Status**: Partially Implemented (mail system complete, parallel batch mode not yet active)
**Original Session**: 14848423526856432295
**Created**: 2026-01-11

---

## Overview

This directory contains complete documentation for implementing **parallel persona execution** in the Jules scheduler. This is a major architectural improvement that will reduce sprint cycle time from 23+ ticks to <6 ticks (~75% speedup).

---

## Problem Being Solved

### Current State (Sequential)
```
Tick 1:  Curator runs     → creates PR #1
Tick 2:  Refactor runs    → creates PR #2
Tick 3:  Visionary runs   → creates PR #3
...
Tick 23: Steward runs     → creates PR #23

Total: 23+ ticks per sprint
```

### Target State (Parallel)
```
Tick 1:  ALL personas run in parallel → create PRs #1-23
Tick 2:  Weaver integrates patches    → merges clean PRs, reports conflicts
Tick 3:  Conflicted personas re-run   → fix and resubmit
Tick 4:  Weaver re-integrates         → final merge

Total: 4-6 ticks per sprint (75% faster)
```

---

## Architecture

### Key Components

1. **Mail System** - Async messaging between personas and weaver
   - Append-only JSONL event log
   - Ibis + DuckDB for querying
   - CLI tool for send/read operations

2. **Patch-Based Integration** - Weaver uses `git apply` instead of `git merge`
   - Downloads `.patch` files from PRs
   - Tests applicability with `git apply --check`
   - Applies clean patches, reports conflicts via mail

3. **Mailbox Consolidation** - Scheduler checks mailboxes at each tick
   - Re-runs personas that have unread messages
   - Creates feedback loop for conflict resolution

4. **Parallel Batch Mode** - Scheduler launches personas simultaneously
   - Feature-flagged rollout (every 5th sprint initially)
   - Falls back to sequential mode if issues occur

### Why This Design?

**Patch-Based**: Jules has sandbox limitations with git operations. `git apply` is safe and reliable, while `git merge`/`git rebase` are unreliable.

**Mail System**: Need async communication since personas run at different times. Mail provides a simple, append-only, debuggable interface.

**Gradual Rollout**: Parallel mode is risky. Start with feature flag (every 5th sprint) to test in production before making it default.

---

## Documents in This Package

### 1. `PARALLEL_PERSONAS_PLAN.md` (Comprehensive)

**Purpose**: Full architectural plan with all details

**Contents**:
- Problem statement and motivation
- Complete architecture diagrams
- Implementation for each component
- Rollout strategy and phases
- Monitoring, debugging, and troubleshooting
- Risk mitigation strategies
- Example workflows and CLI usage

**When to Use**: Reference document for understanding the full system

**Size**: ~2000 lines, ~40 pages

---

### 2. `PARALLEL_PERSONAS_PROMPT.md` (Actionable)

**Purpose**: Concise prompt for launching a new Jules session

**Contents**:
- What to build (mail system, weaver update, scheduler changes)
- Implementation order (priority 1-3)
- Key technical constraints (what works in Jules sandbox)
- Success criteria
- Reference documents to read first

**When to Use**: Copy this as the prompt when creating a new Jules session

**Size**: ~500 lines, ~10 pages

---

### 3. This README

**Purpose**: Navigation guide for the documentation package

**When to Use**: Start here to understand what's available

---

## How to Use This Documentation

### Option 1: Create New Jules Session (Recommended)

Use the concise prompt to launch a fresh implementation:

```bash
# 1. Read the prompt file
cat .team/PARALLEL_PERSONAS_PROMPT.md

# 2. Create Jules session with this prompt
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '.team')
from repo.client import JulesClient

client = JulesClient()

# Read the prompt
with open('.team/PARALLEL_PERSONAS_PROMPT.md') as f:
    prompt = f.read()

# Create session
session = client.create_session(
    prompt=prompt,
    title="Implement Parallel Persona Workflow",
    source_context={
        "source": "sources/github/franklinbaldo/egregora",
        "githubRepoContext": {"startingBranch": "main"}
    },
    require_plan_approval=True,  # Get plan approval first
    automation_mode="AUTO_CREATE_PR"
)

print(f"Created session: {session['id']}")
print(f"URL: https://jules.google.com/sessions/{session['id']}")
PYTHON_EOF
```

### Option 2: Resume Existing Session

Session 14848423526856432295 is already IN_PROGRESS implementing the mail backend. You can:

1. **Let it finish** - It has guidance and should complete the mail system soon
2. **Check status** - See `.team/repo/client.py` for API usage
3. **Provide feedback** - Send additional messages if needed

### Option 3: Manual Implementation

Use the plan as a guide for human implementation:

1. Read `PARALLEL_PERSONAS_PLAN.md`
2. Follow the implementation roadmap (Phase 1-5)
3. Use the code examples and specifications

---

## Quick Reference

### Key Files to Modify

```
.team/
├── repo/
│   ├── mail.py                    # NEW - Mail backend
│   ├── mail_cli.py               # NEW - Mail CLI tool
│   ├── scheduler_v2.py           # MODIFY - Add parallel mode
│   └── scheduler_managers.py     # MODIFY - Add batch support
├── personas/
│   ├── weaver/prompt.md          # MODIFY - New integration role
│   └── */prompt.md               # MODIFY - Add mailbox check (all 23)
└── mail/
    └── events.jsonl              # NEW - Mail event log
```

### Key Dependencies

```toml
# Add to pyproject.toml
typer = "^0.9.0"  # For mail CLI

# Already present (no changes)
ibis-framework[duckdb]  # For mail backend
pydantic  # For data validation
```

### Testing Commands

```bash
# Test mail backend
pytest tests/unit/repo/mail/ -v

# Test CLI manually
jules-mail send --to curator --subject "Test" --body "Hello"
jules-mail inbox --persona curator

# Test scheduler (dry-run)
python .team/repo/scheduler_v2.py --dry-run --mode cycle

# Test weaver manually
# (create test PRs, run weaver session, verify patch application)
```

---

## Implementation Timeline

### Week 1: Foundation
- ✅ Mail backend (`repo/mail.py`)
- ✅ Mail CLI (`repo/mail_cli.py`)
- ✅ Comprehensive tests

**Deliverable**: Working mail system with CLI

### Week 2: Integration
- ✅ Rewrite weaver prompt
- ✅ Test patch-based integration
- ✅ Add scheduler parallel mode

**Deliverable**: Weaver can integrate patches and report conflicts

### Week 3: Rollout
- ✅ Update all persona prompts
- ✅ Feature flag for gradual rollout
- ✅ End-to-end testing

**Deliverable**: First parallel sprint completes successfully

### Week 4: Stabilization
- ✅ Monitor and fix issues
- ✅ Performance tuning
- ✅ Documentation updates

**Deliverable**: Stable parallel mode ready for wider adoption

---

## Success Metrics

### Performance
- Sprint cycle time: 23+ ticks → <6 ticks (75% reduction)
- PRs per sprint: 20-23 PRs (same or higher)
- Time to PR merge: <1 hour (vs several hours)

### Quality
- Conflict rate: <20% (most PRs merge cleanly)
- Resolution time: 1-2 ticks (quick feedback loop)
- Test coverage: >80% (especially mail backend)

### Reliability
- No data loss in mail system (append-only guarantees)
- No regressions in sequential mode
- Graceful handling of timeouts/errors

---

## Related Sessions

### Session 14848423526856432295
- **Status**: IN_PROGRESS (unstuck as of 2026-01-11 12:48 UTC)
- **Focus**: Implementing mail backend and CLI
- **Current Work**: Fixing Ibis schema issues in mail system
- **URL**: https://jules.google.com/sessions/14848423526856432295

**Note**: This session received guidance on 2026-01-11 and should complete the mail backend implementation. You can either:
- Wait for it to finish (check status with Jules API)
- Create a new session with the prompt above (fresh start)

---

## Key Design Decisions

### 1. Why Patches Instead of Git Merge?

**Answer**: Jules runs in a sandbox with limited git capabilities.

- ✅ `git apply` works reliably with downloaded `.patch` files
- ❌ `git merge` and `git rebase` are unreliable (interactive, network issues)
- GitHub provides `.patch` URLs for every PR (e.g., `/pull/123.patch`)

### 2. Why JSONL Instead of Database?

**Answer**: Align with egregora's philosophy and simplify architecture.

- Append-only = crash-safe, easy to backup
- No external dependencies (PostgreSQL, Redis, etc.)
- DuckDB + Ibis for efficient querying (already used by egregora)
- Easy to inspect and debug (plain text, human-readable)

### 3. Why Feature Flag Rollout?

**Answer**: Parallel execution is complex and risky.

- Start with 20% (every 5th sprint) to test in production
- Monitor for issues before making it default
- Easy to disable if problems occur
- Gradual confidence building

### 4. Why Weaver as Integrator?

**Answer**: Reuse existing persona instead of creating new one.

- Weaver is already defined as "Integration & builds"
- Avoid persona proliferation (23 is already a lot)
- Weaver prompt can be rewritten to focus on this role

---

## Troubleshooting

### Issue: Session Gets Stuck on Mail Tests

**Symptom**: Tests fail with empty inbox or schema errors

**Solution**:
- Remove `DUCKDB_EVENT_COLUMNS` duplication (use only Ibis schema)
- For array operations, use `ibis.literal(x).isin(_.array)` not `_.array.contains(x)`
- Handle empty files with `ibis.memtable([], schema=EVENT_SCHEMA)`

See session 14848423526856432295 activities for full debugging history.

### Issue: Weaver Can't Download Patches

**Symptom**: `curl` fails with 404 or auth errors

**Solution**:
- Verify PR is open and number is correct
- For private repos, use: `curl -H "Authorization: Bearer $GITHUB_TOKEN"`
- Check GitHub rate limits: `gh api rate_limit`

### Issue: `git apply` Fails Unexpectedly

**Symptom**: Patch looks clean but apply fails

**Solution**:
- Check CRLF settings: `git config core.autocrlf false`
- Ensure clean working tree: `git status`
- Try three-way merge: `git apply --3way`

---

## FAQ

### Q: Can we run ALL personas in parallel or just some?

**A**: Start with all personas in parallel (simplest). Later, optimize by grouping dependent personas sequentially (e.g., docs personas together).

### Q: What if weaver session times out processing 20+ patches?

**A**: Increase weaver timeout to 60-90 minutes. If still an issue, process patches in batches (10 at a time) or parallelize weaver itself (multiple weaver sessions).

### Q: Should mail events be committed to git or ignored?

**A**: Gitignore them (like logs). They're transient state, not source code. Backup separately if needed for debugging.

### Q: What happens if a persona fails repeatedly after conflicts?

**A**: Set max retries (e.g., 3 attempts), then skip and notify user. Add manual intervention fallback for critical personas.

---

## Getting Help

### In this Repo
- Read `CLAUDE.md` for project coding standards
- Read `.team/README.md` for personas overview
- Read `src/egregora/database/` for Ibis examples

### External Resources
- [Ibis Documentation](https://ibis-project.org/)
- [DuckDB JSON Support](https://duckdb.org/docs/data/json/overview)
- [Git Apply Docs](https://git-scm.com/docs/git-apply)
- [Jules API Docs](https://developers.google.com/repo/api)

### Contact
- Open GitHub issue for bugs/questions
- Check Jules session activities for conversation history

---

**Last Updated**: 2026-01-11
**Created By**: Claude Sonnet 4.5 (analyzing session 14848423526856432295)
**Status**: Ready for implementation via new Jules session

---

## Next Steps

1. **Option A (Recommended)**: Create new Jules session with `PARALLEL_PERSONAS_PROMPT.md`
2. **Option B**: Wait for session 14848423526856432295 to complete mail backend
3. **Option C**: Implement manually using `PARALLEL_PERSONAS_PLAN.md` as guide

Choose based on urgency and preference for autonomous vs manual implementation.

Good luck! This will be a significant improvement to Jules' efficiency. 🚀
