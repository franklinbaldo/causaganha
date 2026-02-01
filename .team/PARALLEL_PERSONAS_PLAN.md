# Parallel Personas Implementation Plan

> **Note (2026-01-29):** Historical planning document. The team now has **21 personas** (20 AI + 1 human), not 23. References to Refactor, Sheriff, Simplifier, Organizer, Weaver, Steward are outdated -- these personas have been deleted or archived. The mail system and scheduler described here have been partially implemented via `stateless.py` (round-robin mode). Prompts now use the **ROSAV framework**.

**Status**: Partially Implemented
**Priority**: High
**Estimated Complexity**: Medium-High
**Original Session**: 14848423526856432295

---

## Executive Summary

Transform the Jules scheduler from **sequential persona execution** to **parallel batch execution** with automated conflict resolution. This enables multiple personas to work simultaneously on different aspects of the codebase, significantly reducing sprint cycle time from ~20+ ticks to potentially 2-3 ticks.

**Current State**: Personas run one-at-a-time in a fixed order (Curator → Refactor → Visionary → ...)
**Target State**: Personas run in parallel batches with a central integrator managing conflicts

---

## Problem Statement

### Current Limitations

1. **Sequential Bottleneck**: 23 personas must run one after another, taking 23+ ticks to complete a sprint
2. **Idle Time**: While one persona works, all others are idle
3. **No Parallelization**: Tasks that could run independently still wait in queue
4. **Slow Feedback Loops**: Issues discovered late in the cycle require restarting from the beginning

### Why This Matters

- **Developer Productivity**: Faster sprint cycles mean quicker iterations
- **Resource Utilization**: Better use of available compute resources
- **Scalability**: Can handle more personas without linear time increase
- **Autonomy**: Reduces need for manual intervention in PR merging

---

## Solution Architecture

### High-Level Workflow

```
Tick 1: Launch Parallel Batch
├─ Curator   (creates PR #101 with patch)
├─ Refactor  (creates PR #102 with patch)
├─ Visionary (creates PR #103 with patch)
└─ ... (all personas execute simultaneously)

Tick 2: Weaver Integration
├─ Downloads .patch files from PRs #101-123
├─ Applies patches sequentially to clean jules branch
├─ For each patch:
│   ├─ git apply succeeds → Keep it, auto-merge PR
│   └─ git apply fails → Send message to original persona with conflict details
└─ Creates consolidated PR with all successful patches

Tick 3: Persona Fixes (if needed)
├─ Personas receive conflict messages from their mailboxes
├─ Re-run only the personas that had conflicts
└─ Repeat weaver integration
```

### Key Design Decisions

#### 1. **Patch-Based Integration** (Not Git Merge)

**Reasoning**: Jules has limited git capabilities due to sandbox restrictions.

- ✅ **Can do**: `git apply` with patch files (reliable, safe)
- ❌ **Cannot do**: Complex `git pull`, `git rebase`, `git merge` operations (unreliable in sandbox)

**Implementation**:

- Personas create PRs as usual
- Weaver downloads `.patch` files from GitHub (e.g., `https://github.com/owner/repo/pull/123.patch`)
- Uses `git apply --check` to test applicability
- Uses `git apply` to apply successful patches

#### 2. **Hybrid S3/Maildir System** (The "Jules Mail" System)

**Reasoning**: Robust, industry-standard storage that works both locally and in high-scale S3 environments (like Internet Archive).

**Architecture**:

- **Local**: Standard `Maildir` format in `.team/mail/{persona_id}/`. Safe, atomic, and human-readable.
- **S3**: `.eml` files stored in `s3://bucket/{persona_id}/{uuid}.eml`.
- **Metadata**: Uses S3 Object Metadata (specifically `x-amz-meta-seen`) to track read status, avoiding the need for a separate database.

**Why S3/Maildir**:

- **Compatibility**: Works across different execution environments.
- **Atomic**: Maildir/S3 operations are naturally atomic, preventing corruption.
- **Rich Context**: Supports standard email headers (Subject, From, To) for future external integration.
- **Scale**: Can handle thousands of messages without performance indexing issues.

#### 3. **Weaver as Integrator**

**Reasoning**: Reuse existing "Integration & builds" persona.

**Required Changes**:

- Update `personas/weaver/prompt.md.j2` to focus on patch integration.
- Add instructions for using the `jules-mail` CLI.

---

## Implementation Components

### 1. Mail Backend (`.team/repo/mail.py`)

**Purpose**: Core mail system for inter-persona communication.

**Requirements**:

- Supported backends: `LocalMaildirBackend`, `S3MailboxBackend`.
- Environment-driven configuration via `JULES_MAIL_STORAGE`.
- Unified interface for sending, listing, and marking messages as read.

**Key Backend logic**:

```python
class MailboxBackend(ABC):
    @abstractmethod
    def send_message(self, from_id, to_id, subject, body, attachments=None): pass
    @abstractmethod
    def list_inbox(self, persona_id, unread_only=False): pass
    @abstractmethod
    def mark_read(self, persona_id, key): pass
```

---

### 2. Mail CLI Tool (`jules-mail`)

**Purpose**: Command-line interface for personas to interact with the Jules Mail system.

**Commands**:

```bash
# Send a message
jules-mail send --to curator --subject "Conflict in PR #123" --body "..."

# Read inbox
jules-mail inbox --persona curator

# Read specific message (interactive or via key)
jules-mail read <message_id> --persona curator
```

**Implementation**:
The `jules-mail` command is registered as an entry point in `pyproject.toml` and points to `repo.mail_cli:app`. It supports both S3 and Local backends seamlessly.

---

### 3. Weaver Persona Update (`personas/weaver/prompt.md`)

**Purpose**: Rewrite weaver to be the integration orchestrator.

**New Responsibilities**:

1. **Collect Patches**: Identify all open PRs from current sprint
2. **Test Applicability**: Use `git apply --check <patch>` for each
3. **Apply Clean Patches**: Use `git apply <patch>` for non-conflicting changes
4. **Report Conflicts**: Send mail to original persona with details
5. **Create Consolidated PR**: Single PR with all successfully applied patches

**Prompt Template** (excerpt):

```markdown
# Weaver: Integration Orchestrator

You are the Weaver, responsible for integrating parallel work from other personas.

## Your Workflow

### 1. Identify Sprint PRs
List all open PRs created by Jules personas in the current sprint:
```bash
gh pr list --label jules-sprint-N --json number,author,title,headRefName
```

### 2. Download Patches

For each PR, download the unified diff:

```bash
curl -L https://github.com/{owner}/{repo}/pull/{pr_number}.patch -o /tmp/pr-{pr_number}.patch
```

### 3. Test Applicability

Create a clean branch from main and test each patch:

```bash
git checkout -b integration-test origin/main
for patch in /tmp/pr-*.patch; do
    if git apply --check "$patch"; then
        echo "✅ $patch applies cleanly"
    else
        echo "❌ $patch has conflicts"
    fi
done
```

### 4. Apply Clean Patches

```bash
git checkout -b jules-sprint-N-integration origin/main
for patch in /tmp/pr-*.patch; do
    git apply --check "$patch" && git apply "$patch" || echo "Skipped $patch"
done
git add -A
git commit -m "chore: integrate sprint N personas"
```

### 5. Report Conflicts

For each failed patch, send mail to the original persona:

```bash
jules-mail send \
    --to <persona_id> \
    --subject "Conflict in PR #<pr_number>" \
    --body "Your PR has merge conflicts. Please rebase on latest main and resubmit.\n\nConflict details:\n<git apply output>"
```

### 6. Create Integration PR

Push the integration branch and create a PR to merge into main:

```bash
git push origin jules-sprint-N-integration
gh pr create --title "Sprint N: Integrated Changes" --body "..."
```

## Tools Available

- `gh`: GitHub CLI for PR management
- `git`: Git operations (apply, checkout, etc.)
- `curl`: Download patches
- `jules-mail`: Send messages to personas

## Important Notes

- Always use `git apply`, never `git merge` or `git rebase` (sandbox limitations)
- Test patches on a clean branch from main (avoid contamination)
- Be descriptive in conflict messages (help personas fix issues)
- Auto-merge PRs that applied cleanly (use `gh pr merge`)

```

### 4. Scheduler Updates (`repo/scheduler_v2.py`)

**Purpose**: Add parallel batch mode and mailbox consolidation.

**Changes Required**:

#### A. Add Parallel Batch Mode

```python
def run_parallel_batch(
    personas: list[str],
    sprint_manager: SprintManager,
    orchestrator: SessionOrchestrator,
    dry_run: bool = False,
) -> dict[str, str]:
    """Launch multiple personas simultaneously.

    Returns:
        dict mapping persona_id -> session_id
    """
    sessions = {}
    for persona_id in personas:
        session_id = orchestrator.create_persona_session(
            persona_id=persona_id,
            sprint_num=sprint_manager.current_sprint,
        )
        sessions[persona_id] = session_id
        print(f"🚀 Launched {persona_id}: {session_id}")

    return sessions
```

#### B. Add Mailbox Consolidation

```python
def consolidate_mailboxes(
    personas: list[str],
    orchestrator: SessionOrchestrator,
) -> None:
    """Check mailboxes and re-run personas with messages.

    Called at each tick to handle async feedback from weaver.
    """
    from repo.mail import list_inbox

    for persona_id in personas:
        inbox = list_inbox(persona_id, unread_only=True)
        if inbox:
            print(f"📬 {persona_id} has {len(inbox)} unread message(s)")
            # Create new session to handle messages
            orchestrator.create_persona_session(
                persona_id=persona_id,
                context=f"You have {len(inbox)} messages. Read with: jules-mail inbox --persona {persona_id}",
            )
```

#### C. Update Main Loop

```python
def run_cycle_mode(...):
    # ... existing setup ...

    # Check if this is a batch sprint
    if sprint_manager.current_sprint % 5 == 0:  # Every 5th sprint is parallel
        print("🔀 Running PARALLEL batch mode")

        # Launch all personas
        sessions = run_parallel_batch(
            personas=list(personas.keys()),
            sprint_manager=sprint_manager,
            orchestrator=orchestrator,
            dry_run=dry_run,
        )

        # Wait for completion (or timeout)
        # ... poll session states ...

        # Run weaver integration
        weaver_session = orchestrator.create_persona_session("weaver", ...)
        # ... wait for weaver ...

        # Check mailboxes for conflict reports
        consolidate_mailboxes(list(personas.keys()), orchestrator)

    else:
        # Normal sequential mode
        # ... existing code ...

    # Always check mailboxes at end of tick
    consolidate_mailboxes(list(personas.keys()), orchestrator)
```

---

### 5. Persona Prompt Updates

**Purpose**: Teach all personas to check their mailboxes.

**Add to ALL Persona Prompts** (prepend to existing prompts):

```markdown
## Mailbox Check (IMPORTANT)

Before starting your work, check your mailbox for messages:

```bash
jules-mail inbox --persona {persona_id}
```

If you have messages:

1. Read each message: `jules-mail read <message_key> --persona {persona_id}`
2. Address the feedback (e.g., fix conflicts, rebase, etc.)
3. Proceed with your work

Common message types:

- **Conflict Reports**: Your PR couldn't be merged due to conflicts
- **Feedback**: Requested changes or improvements
- **Coordination**: Other personas need your input

## Your Work

[... existing persona-specific instructions ...]

```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)

**Goal**: Build and test mail backend

1. ✅ Implement `repo/mail.py` with Ibis schema (no DuckDB duplication)
2. ✅ Create comprehensive tests for mail backend
3. ✅ Implement `repo/mail_cli.py` with Typer
4. ✅ Test CLI with manual sends/reads
5. ✅ Document mail API and CLI usage

**Success Criteria**:
- All tests pass
- CLI can send/read/tag messages
- Mailbox projections work correctly

### Phase 2: Weaver Integration (Week 1-2)

**Goal**: Enable weaver to integrate patches and report conflicts

### Integration Code
```python
def integrate_patch(pr_number: int, patch_url: str) -> bool:
    # 1. Download patch
    # 2. git apply --check
    # 3. git apply (if safe)
    ...
```

### Integration Execution

```bash
# Example Weaver logic
for pr in prs:
    success = integrate_patch(pr.number, pr.patch_url)
    if not success:
        report_conflict(pr.author, pr.number)
```

1. ✅ Rewrite `personas/weaver/prompt.md` with new responsibilities
2. ✅ Test weaver manually with sample PRs
3. ✅ Verify patch download and `git apply` workflow
4. ✅ Test conflict detection and mail sending
5. ✅ Document weaver workflow

**Success Criteria**:

- Weaver can apply clean patches
- Weaver detects conflicts correctly
- Weaver sends mail with conflict details

### Phase 3: Scheduler Integration (Week 2)

**Goal**: Add parallel batch mode to scheduler

1. ✅ Implement `run_parallel_batch()` in `scheduler_v2.py`
2. ✅ Implement `consolidate_mailboxes()` in `scheduler_v2.py`
3. ✅ Update cycle mode to support batch sprints
4. ✅ Add configuration for batch frequency (every N sprints)
5. ✅ Test with dry-run mode

**Success Criteria**:

- Personas launch in parallel
- Mailbox consolidation triggers re-runs
- No regressions in sequential mode

### Phase 4: Persona Updates (Week 3)

**Goal**: Update all personas to check mailboxes

1. ✅ Prepend mailbox check to all 23 persona prompts
2. ✅ Test each persona with simulated messages
3. ✅ Verify personas read and respond to messages
4. ✅ Document persona mailbox workflow

**Success Criteria**:

- All personas check mailboxes before work
- Personas respond appropriately to messages

### Phase 5: End-to-End Testing (Week 3-4)

**Goal**: Validate full parallel workflow

1. ✅ Run a full parallel sprint (all personas + weaver)
2. ✅ Inject intentional conflicts and verify resolution
3. ✅ Monitor for edge cases (timeouts, errors, etc.)
4. ✅ Performance testing (time savings vs sequential)
5. ✅ Create runbook for monitoring and debugging

**Success Criteria**:

- Complete sprint in <5 ticks (vs 23+ ticks sequential)
- Conflicts are detected and resolved
- No data loss or corruption

---

## Technical Requirements

### Dependencies

**Existing (no changes needed)**:

- `ibis-framework[duckdb]` - Already in use for egregora
- `typer` - Need to add for CLI

**New**:

```toml
[tool.uv.dependencies]
typer = "^0.9.0"  # For mail CLI
```

### File Structure

```
.team/
├── repo/
│   ├── mail.py                    # NEW: Mail backend
│   ├── mail_cli.py               # NEW: Mail CLI tool
│   ├── scheduler_v2.py           # MODIFIED: Add parallel mode
│   └── scheduler_managers.py     # MODIFIED: Add batch support
├── personas/
│   ├── weaver/
│   │   └── prompt.md             # MODIFIED: New integration role
│   ├── curator/
│   │   └── prompt.md             # MODIFIED: Add mailbox check
│   └── ... (all personas)        # MODIFIED: Add mailbox check
├── mail/
│   └── events.jsonl              # NEW: Append-only mail log
└── tests/
    └── unit/repo/mail/
        └── test_mail.py          # NEW: Mail backend tests
```

### GitHub API Requirements

**Patch Download**: Use public GitHub URLs (no auth needed)

```bash
# Works for public repos
curl -L https://github.com/owner/repo/pull/123.patch
```

**For Private Repos**: Use GitHub token

```bash
curl -L -H "Authorization: Bearer $GITHUB_TOKEN" \
    https://github.com/owner/repo/pull/123.patch
```

### Git Operations

**Safe Operations** (Jules can do these):

- `git apply --check <patch>` - Test patch applicability
- `git apply <patch>` - Apply patch to working tree
- `git checkout -b <branch>` - Create new branch
- `git add -A` - Stage all changes
- `git commit -m "..."` - Create commit

**Unsafe Operations** (Jules should avoid):

- `git merge` - Complex, can fail in sandbox
- `git rebase` - Interactive, not reliable
- `git pull` - Network + merge, unpredictable

---

## Rollout Strategy

### Stage 1: Feature Flag (Week 1-2)

Enable parallel mode only on specific sprints:

```python
# In scheduler config
PARALLEL_BATCH_SPRINTS = [50, 55, 60]  # Test on these sprints

if sprint_manager.current_sprint in PARALLEL_BATCH_SPRINTS:
    run_parallel_batch(...)
else:
    run_sequential_cycle(...)
```

### Stage 2: Gradual Rollout (Week 3-4)

Increase frequency:

```python
# Every 5th sprint
if sprint_manager.current_sprint % 5 == 0:
    run_parallel_batch(...)
```

### Stage 3: Default Mode (Week 4+)

Make parallel the default, sequential the fallback:

```python
# Always parallel, unless flagged otherwise
if sprint_manager.current_sprint in SEQUENTIAL_ONLY_SPRINTS:
    run_sequential_cycle(...)
else:
    run_parallel_batch(...)
```

---

## Monitoring and Debugging

### Key Metrics

1. **Sprint Cycle Time**: Ticks to complete sprint (target: <5 vs 23+)
2. **Conflict Rate**: % of PRs with conflicts (expect 10-20%)
3. **Resolution Time**: Ticks to resolve conflicts (target: 1-2)
4. **Throughput**: PRs merged per sprint (expect 2-3x increase)

### Debugging Tools

**Mail Inspection**:

```bash
# View raw events
cat .team/mail/events.jsonl | jq .

# Count messages per persona
cat .team/mail/events.jsonl | jq -r '.to_persona' | sort | uniq -c

# Find unread messages
python3 << 'EOF'
from repo.mail import get_inbox
for persona in ["curator", "refactor", "visionary"]:
    inbox = get_inbox(persona, unread_only=True)
    print(f"{persona}: {len(inbox)} unread")
EOF
```

**Weaver Logs**:

```bash
# Check weaver session logs
gh api repos/{owner}/{repo}/actions/runs?branch=weaver-session-* | jq .
```

**Scheduler State**:

```bash
# Check current sprint state
cat .team/cycle_state.json | jq .
```

### Common Issues

#### Issue: Weaver Can't Download Patches

**Symptom**: `curl` fails with 404 or auth errors
**Solution**:

- Verify PR number is correct
- Check if repo is private (need `GITHUB_TOKEN`)
- Ensure PR is still open

#### Issue: `git apply` Fails Unexpectedly

**Symptom**: Patch looks clean but apply fails
**Solution**:

- Check for CRLF issues (`git config core.autocrlf false`)
- Verify working tree is clean (`git status`)
- Try `git apply --3way` (three-way merge)

#### Issue: Personas Ignore Mailbox

**Symptom**: Messages sent but personas don't respond
**Solution**:

- Verify persona prompt includes mailbox check
- Check if CLI is accessible (`which jules-mail`)
- Manually test: `jules-mail inbox --persona <id>`

#### Issue: Mail Events Corrupted

**Symptom**: DuckDB errors when reading events
**Solution**:

- Validate JSONL format: `cat events.jsonl | jq empty`
- Check for duplicate event_ids
- Restore from backup if needed

---

## Success Criteria

### Functional Requirements

- ✅ Personas run in parallel batches
- ✅ Weaver integrates patches using `git apply`
- ✅ Conflicts are detected and reported via mail
- ✅ Personas respond to mailbox messages
- ✅ Sequential mode still works (no regressions)

### Performance Requirements

- ✅ Sprint cycle time reduced by 75% (23 ticks → <6 ticks)
- ✅ Mail system handles 100+ messages without performance degradation
- ✅ Weaver processes 20+ patches in <5 minutes

### Quality Requirements

- ✅ Test coverage >80% for mail backend
- ✅ No data loss in mail system (append-only guarantees)
- ✅ Graceful handling of timeouts and errors
- ✅ Clear documentation for debugging

---

## Risk Mitigation

### Risk: Conflict Storms

**Description**: Many personas have conflicts, leading to cascading failures
**Likelihood**: Medium
**Impact**: High
**Mitigation**:

- Set max retries per persona (e.g., 3 attempts)
- Skip personas that fail repeatedly
- Manual intervention fallback

### Risk: Mail System Corruption

**Description**: JSONL file becomes corrupted or unreadable
**Likelihood**: Low
**Impact**: High
**Mitigation**:

- Backup `events.jsonl` before each sprint
- Add validation on append (JSON syntax check)
- Recovery tool to rebuild from valid events

### Risk: Weaver Overwhelm

**Description**: Weaver can't handle 20+ patches in one session
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:

- Process patches in batches (e.g., 10 at a time)
- Increase weaver timeout to 90 minutes
- Parallelize weaver if needed (multiple weaver sessions)

### Risk: Git Sandbox Limitations

**Description**: `git apply` fails due to sandbox restrictions
**Likelihood**: Low
**Impact**: High
**Mitigation**:

- Extensive testing in sandbox environment
- Fallback to GitHub API for patch application (slower but reliable)
- Manual merge option for critical patches

---

## Future Enhancements

### Phase 6: Smart Batching

- Group personas by dependency (e.g., docs personas together)
- Avoid conflicts by scheduling dependent personas sequentially
- Use ML to predict conflict probability

### Phase 7: Distributed Weaver

- Split weaver into multiple parallel sessions
- Each weaver handles a subset of patches
- Final weaver consolidates all partial integrations

### Phase 8: Interactive Conflict Resolution

- Weaver proposes conflict resolution strategies
- Personas can negotiate patch order
- AI-assisted merge conflict resolution

---

## References

### Code Files

- `.team/repo/scheduler_v2.py` - Main scheduler logic
- `.team/repo/scheduler_managers.py` - Session orchestration
- `.team/personas/weaver/prompt.md` - Weaver persona definition
- `src/egregora/database/` - Ibis patterns and DuckDB usage

### Documentation

- `CLAUDE.md` - Project coding standards
- `.team/README.md` - Jules personas overview
- Original session: 14848423526856432295

### External Resources

- [Ibis Documentation](https://ibis-project.org/)
- [DuckDB JSON Support](https://duckdb.org/docs/data/json/overview)
- [Git Apply Documentation](https://git-scm.com/docs/git-apply)

---

## Appendix A: Example Mail Flow

```
Sprint N starts
├─ Tick 1: Parallel Launch
│   ├─ curator creates PR #101
│   ├─ refactor creates PR #102
│   └─ visionary creates PR #103
│
├─ Tick 2: Weaver Integration
│   ├─ Downloads .patch for #101, #102, #103
│   ├─ git apply #101 → ✅ Success
│   ├─ git apply #102 → ❌ Conflict with #101
│   ├─ git apply #103 → ✅ Success
│   ├─ Sends mail:
│   │   └─ To: refactor
│   │       Subject: "Conflict in PR #102"
│   │       Body: "Your changes conflict with curator's PR #101..."
│   └─ Creates PR #104 with #101 + #103 merged
│
├─ Tick 3: Mailbox Consolidation
│   ├─ refactor checks mailbox
│   ├─ Reads conflict message
│   ├─ Rebases PR #102 on latest main
│   └─ Updates PR #102
│
└─ Tick 4: Weaver Re-Integration
    ├─ Downloads .patch for #102 (updated)
    ├─ git apply #102 → ✅ Success
    └─ Updates PR #104, auto-merges

Sprint N complete (4 ticks vs 23 sequential)
```

---

## Appendix B: CLI Usage Examples

### Sending Messages

```bash
# Simple message
jules-mail send --to curator --subject "Question" --body "Can you review X?"

# With attachments
jules-mail send \
    --to refactor \
    --subject "Conflict in PR #123" \
    --body "See attached patch for conflicts" \
    --attach https://github.com/owner/repo/pull/123.patch

# From environment variable (persona auto-detected)
export JULES_PERSONA=weaver
jules-mail send --to curator --subject "..." --body "..."
```

### Reading Inbox

```bash
# List all messages
jules-mail inbox --persona curator

# Unread only
jules-mail inbox --persona curator --unread

# Read specific message
jules-mail read 42 --persona curator

# Output as JSON
jules-mail inbox --persona curator --json
```

### Tagging Messages

```bash
# Add tag
jules-mail tag add 42 needs-action --persona curator

# Remove tag
jules-mail tag rm 42 needs-action --persona curator

# List tags
jules-mail tag ls 42 --persona curator
```

---

**End of Plan**
