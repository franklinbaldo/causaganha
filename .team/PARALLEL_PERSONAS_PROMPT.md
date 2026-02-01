# Jules Session Prompt: Implement Parallel Persona Workflow

> **Note (2026-01-29):** Historical prompt document. The team now has **21 personas** (20 AI + 1 human), not 23. The mail system has been implemented. The scheduler now uses `stateless.py` with round-robin mode. References to deleted personas (Refactor, Sheriff, Simplifier, Organizer, Weaver) are outdated. Prompts use the **ROSAV framework**.

## Context

The Jules scheduler currently runs 21 personas **sequentially** (one after another) via round-robin. This is inefficient because many personas work on independent parts of the codebase and could run in parallel.

**Goal**: Transform to **parallel batch execution** where multiple personas run simultaneously, with automated conflict resolution.

**Expected Outcome**: Significant reduction in sprint cycle time.

---

## What You Need to Build

### 1. Mail System (`repo/mail.py` + `repo/mail_cli.py`)

**Purpose**: Enable async communication between personas and the weaver.

**Core Components**:
- Append-only JSONL event log (`.team/mail/events.jsonl`)
- Ibis + DuckDB for querying mailbox projections
- CLI tool for sending/reading messages (`jules-mail`)

**Key Operations**:
```python
# Backend API
send_message(from_persona, to_persona, subject, body, attachments=[])
get_inbox(persona_id, unread_only=False) -> list[Message]
mark_read(persona_id, message_id)

# CLI
jules-mail send --to curator --subject "..." --body "..."
jules-mail inbox --persona curator
jules-mail read <msg_id> --persona curator
```

**Critical Implementation Notes**:
1. Use **only Ibis schema** (no DuckDB duplication) - this was causing bugs
2. For array operations, use `ibis.literal(x).isin(_.array_col)` not `_.array_col.contains(x)`
3. Handle empty files with `ibis.memtable([], schema=EVENT_SCHEMA)`
4. Follow egregora patterns (see `CLAUDE.md` and `src/egregora/database/`)

### 2. Weaver Persona Update (`personas/weaver/prompt.md`)

**Purpose**: Transform weaver into the integration orchestrator.

**New Workflow**:
```bash
# 1. List sprint PRs
gh pr list --label jules-sprint-N --json number,headRefName

# 2. Download patches
curl -L https://github.com/{owner}/{repo}/pull/{num}.patch -o /tmp/pr-{num}.patch

# 3. Test each patch
git checkout -b integration-test origin/main
git apply --check /tmp/pr-*.patch  # Check for conflicts

# 4. Apply clean patches
git checkout -b jules-sprint-N-integration origin/main
for patch in /tmp/pr-*.patch; do
    git apply "$patch" || echo "Skipped $patch (conflict)"
done

# 5. Send conflict messages
jules-mail send \
    --to <original_persona> \
    --subject "Conflict in PR #X" \
    --body "Your PR conflicts with ... Please rebase and resubmit."

# 6. Create integration PR
gh pr create --title "Sprint N: Integrated Changes" ...
```

**Key Design Decision**: Use `git apply` with patches, NOT `git merge`/`git rebase` (sandbox limitations).

### 3. Scheduler Updates (`repo/scheduler_v2.py`)

**Add Two New Functions**:

```python
def run_parallel_batch(personas, sprint_manager, orchestrator, dry_run=False):
    """Launch all personas simultaneously, return dict[persona_id -> session_id]."""
    sessions = {}
    for persona_id in personas:
        session_id = orchestrator.create_persona_session(persona_id, ...)
        sessions[persona_id] = session_id
    return sessions

def consolidate_mailboxes(personas, orchestrator):
    """Check each persona's inbox and re-run if they have messages."""
    from repo.mail import get_inbox
    for persona_id in personas:
        inbox = get_inbox(persona_id, unread_only=True)
        if inbox:
            print(f"📬 {persona_id} has {len(inbox)} messages")
            orchestrator.create_persona_session(persona_id, ...)
```

**Update Main Loop**:
```python
# Every 5th sprint = parallel mode (for gradual rollout)
if sprint_manager.current_sprint % 5 == 0:
    sessions = run_parallel_batch(personas, ...)
    # Wait for all to complete...
    # Run weaver integration...
    consolidate_mailboxes(personas, ...)  # Check for conflict reports
else:
    # Normal sequential mode (existing code)
    ...

# Always check mailboxes at end of tick
consolidate_mailboxes(personas, orchestrator)
```

### 4. Update All Persona Prompts

**Prepend to ALL persona prompts** (now handled by base template blocks):

```markdown
## 📬 Check Your Mailbox (IMPORTANT)

Before starting work, check for messages:
```bash
jules-mail inbox --persona {persona_id}
```

If you have messages:
1. Read each: `jules-mail read <msg_id> --persona {persona_id}`
2. Address feedback (fix conflicts, rebase, etc.)
3. Mark as read (automatic when you read)
4. Then proceed with your normal work

Common message types:
- **Conflict Reports**: Your PR couldn't merge (conflicts with other PRs)
- **Feedback**: Requested changes
- **Coordination**: Other personas need your input
```

---

## Implementation Order

1. **Mail Backend** (Priority 1)
   - Implement `repo/mail.py` with Ibis-only schema
   - Create comprehensive tests
   - Verify append-only JSONL works correctly

2. **Mail CLI** (Priority 1)
   - Implement `repo/mail_cli.py` with Typer
   - Test manually with send/read/tag operations
   - Document CLI usage

3. **Weaver Update** (Priority 2)
   - Rewrite `personas/weaver/prompt.md`
   - Test patch download and `git apply` workflow
   - Verify conflict detection works

4. **Scheduler Integration** (Priority 2)
   - Add `run_parallel_batch()` and `consolidate_mailboxes()`
   - Test with dry-run mode
   - Gradual rollout (every 5th sprint)

5. **Persona Updates** (Priority 3) - ✅ DONE
   - Mailbox check is now in base template blocks (session_continuity, communication, session_protocol)
   - All 21 personas inherit these blocks via ROSAV framework

6. **End-to-End Testing** (Priority 3)
   - Run full parallel sprint
   - Inject intentional conflicts
   - Verify resolution loop works

---

## Key Technical Constraints

### Git Operations (Jules Can Do)
✅ `git apply --check <patch>` - Test patch
✅ `git apply <patch>` - Apply patch
✅ `git checkout -b <branch>` - Create branch
✅ `git add -A` - Stage changes
✅ `git commit` - Create commit

### Git Operations (Jules Should Avoid)
❌ `git merge` - Unreliable in sandbox
❌ `git rebase` - Interactive, not reliable
❌ `git pull` - Network + merge issues

### Why Patch-Based Integration?
- GitHub provides `.patch` files for every PR
- `git apply` is deterministic and safe
- No complex git history manipulation needed
- Works reliably in sandboxed environments

---

## Reference Documents

**Read These Before Starting**:
1. `.team/PARALLEL_PERSONAS_PLAN.md` - Full detailed plan (this prompt's source)
2. `CLAUDE.md` - Project coding standards (Ibis patterns, type safety, etc.)
3. `.team/README.md` - Existing personas and scheduler architecture
4. `src/egregora/database/` - Examples of Ibis + DuckDB usage in egregora

**Existing Code to Study**:
- `.team/repo/scheduler_v2.py` - Current sequential scheduler
- `.team/repo/scheduler_managers.py` - Session orchestration
- `.team/personas/weaver/prompt.md` - Current weaver definition (will be replaced)

---

## Success Criteria

**Functional**:
- ✅ Mail system sends/receives messages reliably
- ✅ Personas run in parallel and create PRs
- ✅ Weaver integrates patches using `git apply`
- ✅ Conflicts are detected and reported via mail
- ✅ Personas respond to mailbox messages and fix conflicts

**Performance**:
- ✅ Sprint cycle reduced from 23+ ticks to <6 ticks
- ✅ Mail system handles 100+ messages without issues
- ✅ Weaver processes 20+ patches in <5 minutes

**Quality**:
- ✅ Test coverage >80% for mail backend
- ✅ No regressions in sequential mode
- ✅ Clear documentation and debugging tools

---

## Questions to Clarify (If Needed)

1. **Mail Storage Location**: Should `.team/mail/events.jsonl` be gitignored or committed?
   - **Suggested**: Gitignore (transient state, like logs)

2. **Weaver Timeout**: Should we increase weaver session timeout from default 30min to 60min?
   - **Suggested**: Yes, processing 20+ patches takes time

3. **Parallel Frequency**: Start with every 5th sprint (20% parallel)? Or more aggressive?
   - **Suggested**: Every 5th sprint for first month, then increase

4. **Conflict Retry Limit**: How many times should a persona retry after conflicts?
   - **Suggested**: 3 attempts, then skip and notify user

---

## Implementation Tips

### For Mail Backend
- Start with **simplest possible schema** (don't over-engineer)
- Use `pytest` fixtures for test data
- Test empty file edge case thoroughly
- Use Ibis `memtable` for tests (fast, in-memory)

### For Weaver
- Test with **real PRs** from previous sprints
- Handle edge cases: closed PRs, deleted branches, empty patches
- Make conflict messages **actionable** (include exact commands to fix)

### For Scheduler
- Keep parallel mode **optional** (feature flag)
- Add **dry-run mode** for testing
- Log everything (helps debugging)

### For Personas
- Keep mailbox check instructions **simple**
- Don't require personas to handle mail edge cases (scheduler handles it)

---

## Rollout Strategy

**Week 1**: Build mail backend + CLI, get tests passing
**Week 2**: Update weaver, test patch integration manually
**Week 3**: Integrate into scheduler with feature flag (every 5th sprint)
**Week 4**: Update all personas, run full E2E test
**Week 5+**: Monitor, fix issues, increase parallel frequency

---

## Final Notes

- **Read the full plan** (`.team/PARALLEL_PERSONAS_PLAN.md`) for architectural details
- **Follow egregora patterns** - this project has strong conventions (see `CLAUDE.md`)
- **Ship iteratively** - v1 doesn't need to be perfect, focus on working end-to-end
- **Test thoroughly** - parallel systems are complex, invest in testing early
- **Ask for help** - if stuck on sandbox limitations or Ibis queries, ask user

Good luck! This is a significant architectural improvement that will make Jules much more efficient. 🚀

---

**Original Session Reference**: 14848423526856432295
