# 🤖 Jules Automation System

> Autonomous AI agents working together to maintain, improve, and evolve the Egregora codebase

## 📖 Table of Contents

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [Directory Structure](#-directory-structure)
- [Personas](#-personas)
- [Scheduler](#-scheduler)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Persona Development](#-persona-development)
- [Architecture](#-architecture)
- [Troubleshooting](#-troubleshooting)
- [Resources](#-resources)

---

## 🎯 Overview

The Jules automation system is a **multi-agent AI workforce** that maintains and improves the Egregora codebase autonomously. Each agent (persona) has a specialized role and works independently or collaboratively through a sophisticated scheduler.

### Key Features

- **18 Personas (17 AI + 1 Human)** - Each with unique expertise (security, testing, UX, etc.)
- **Autonomous Operation** - Agents create PRs, review code, and coordinate work
- **Round-Robin Scheduling** - Stateless scheduler rotates through all personas automatically
- **Mail System** - Async communication between personas for conflict resolution
- **Journal System** - Each persona maintains work logs for continuity

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions (Every 15 min)                              │
│  ↓                                                           │
│  Scheduler Tick                                             │
│  ↓                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Curator  │→ │ Sentinel │→ │ Visionary│→ │   Bolt   │   │
│  │    🎭    │  │    🛡️    │  │    🔭    │  │    ⚡    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │           │
│      PR #1         PR #2         PR #3         PR #4        │
│       │             │             │             │           │
│       ↓             ↓             ↓             ↓           │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Auto-merge when CI passes                  │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required environment variables
export JULES_API_KEY="your-jules-api-key"
export GITHUB_TOKEN="your-github-token"
export PYTHONPATH=".team"  # For local development
```

### Run the Scheduler

```bash
# Execute one tick (round-robin, next persona)
uv run jules schedule tick

# Dry run (see what would happen)
uv run jules schedule tick --dry-run
```

### Check Persona Mailbox

```bash
# View inbox
uv run mail inbox --persona curator@team

# Send a message
uv run mail send --to curator@team --subject "Fix needed" --body "..."
```

---

## 📁 Directory Structure

```
.team/
├── repo/                      # Scheduler implementation
│   ├── cli/                    # CLI tools (main, mail, my-tools)
│   │   ├── main.py            # Primary CLI entry point
│   │   ├── mail.py            # Mail system CLI
│   │   └── my_tools.py        # Session + mail toolkit
│   ├── core/                   # Core API clients
│   │   ├── client.py          # Jules API client
│   │   ├── github.py          # GitHub API wrapper
│   │   └── exceptions.py      # Shared exceptions
│   ├── features/               # Feature modules
│   │   ├── autofix/           # Auto-fix failed PRs
│   │   ├── feedback/          # Feedback loop system
│   │   ├── mail/              # Mail backend (Maildir)
│   │   ├── polling/           # Session polling
│   │   └── sessions/          # Session management
│   ├── scheduler/              # Scheduler engine
│   │   ├── stateless.py       # Main scheduler (round-robin + Oracle)
│   │   ├── loader.py          # Persona loading
│   │   └── models.py          # Data models
│   └── templates/              # Jinja2 templates
│       ├── base/              # Base templates
│       ├── blocks/            # Reusable blocks
│       └── partials/          # Partial templates
│
├── personas/                   # AI agent definitions (17 personas)
│   ├── absolutist/            # 💯 Legacy code removal
│   ├── artisan/               # 🔨 Code craftsmanship
│   ├── bdd_specialist/        # 🥒 BDD testing expert
│   ├── builder/               # 🏗️ Data architecture
│   ├── essentialist/          # 💎 Radical simplicity
│   ├── evaluator/             # 📊 Round performance evaluation
│   ├── forge/                 # ⚒️ Features, UX, and code cleanup
│   ├── franklin/              # 🧔 Human project lead
│   ├── lore/                  # 📚 System historian
│   ├── maya/                  # 💝 User advocate
│   ├── meta/                  # 🔍 System introspection
│   ├── oracle/                # 🔮 Technical support
│   ├── sapper/                # 💣 Exception structuring
│   ├── scribe/                # ✍️ Documentation
│   ├── sentinel/              # 🛡️ Security audits
│   ├── shepherd/              # 🧑‍🌾 Test coverage
│   ├── streamliner/           # 🌊 Data optimization
│   └── visionary/             # 🔭 Strategic RFCs
│
├── logs/                       # Per-session logs (gitignored)
│   ├── tools_use/             # Tool usage logs per session
│   │   ├── {persona}_{seq}_{timestamp}.csv
│   │   └── ...
│   └── README.md              # Logging system documentation
│
├── mail/                       # Mail system storage
│   └── events.jsonl           # Mail event log
│
├── README.md                  # This file
├── PARALLEL_PERSONAS_*.md     # Parallel execution docs
└── SESSION_ID_PATTERNS.md     # Session ID extraction logic
```

---

## 🤖 Personas

### What is a Persona?

A **persona** is an autonomous AI agent with:

- **Specialized expertise** (security, performance, UX, etc.)
- **Clear responsibilities** defined in `prompt.md.j2`
- **Work journal** documenting past actions
- **Mailbox** for async communication

### Persona Structure

Each persona directory contains:

```
personas/curator/
├── prompt.md.j2           # Persona definition (Jinja2 template)
└── journals/              # Work logs
    ├── archive.md         # Archived journal entries
    ├── 2024-07-26-1400-Initial-Curation-Cycle.md
    └── 2026-01-04-initial-ux-audit.md
```

#### Prompt Template Format

```yaml
---
id: curator              # Unique identifier
emoji: 🎭                # Visual identifier
description: "Opinionated UX/UI designer..."
hired_by: franklin       # Who created this persona
---

{% extends "base/persona.md.j2" %}

{% block role %}
Opinionated UX/UI designer who evaluates generated blogs.
{% endblock %}

{% block goal %}
Evaluate generated blogs and create data-driven UX improvements.
{% endblock %}

{% block context %}
- Reference: docs/ux-vision.md
- Edit templates in src/egregora/output_sinks/mkdocs/
- NEVER edit demo/ directly (generated output)
{% endblock %}

{% block constraints %}
- 100% autonomous (no human placeholders)
- Every feature must be data-driven
{% endblock %}

{% block guardrails %}
✅ Always:
- Create tasks with BDD acceptance criteria
- Document discoveries in ux-vision.md

🚫 Never:
- Propose features requiring human input
- Write code yourself (create tasks instead)
{% endblock %}
```

### Complete Persona List

Persona prompts use the **ROSAV framework** (Role, Objective, Situation, Act, Verify) defined in `.team/repo/templates/base/persona.md.j2`.

| Emoji | Name | Role | Focus Area |
| :---: | :--- | :--- | :--- |
| 💯 | **Absolutist** | Rule Enforcer | Legacy code removal |
| 🔨 | **Artisan** | Craftsman | Code quality and refactoring |
| 🥒 | **BDD Specialist** | Test Expert | Behavior-driven testing |
| 🏗️ | **Builder** | Architect | Data architecture, schemas |
| 💎 | **Essentialist** | Pragmatist | Radical simplicity |
| 📊 | **Evaluator** | Supervisor | Round performance evaluation |
| ⚒️ | **Forge** | Builder | Feature implementation |
| 🧔 | **Franklin** | Human Lead | Project lead (human, not scheduled) |
| 📚 | **Lore** | Historian | System history, ADRs, git forensics |
| 💝 | **Maya** | User Advocate | Non-technical user feedback, doc clarity |
| 🔍 | **Meta** | Introspector | System introspection, prompt evolution |
| 🔮 | **Oracle** | Support Agent | Unblock personas with technical guidance |
| 💣 | **Sapper** | Structurer | Exception handling patterns |
| ✍️ | **Scribe** | Writer | Documentation creation & maintenance |
| 🛡️ | **Sentinel** | Security | Vulnerability scanning |
| 🧑‍🌾 | **Shepherd** | Test Engineer | Test coverage expansion |
| 🌊 | **Streamliner** | Optimizer | Data processing efficiency |
| 🔭 | **Visionary** | Strategist | Strategic RFCs with BDD criteria |

### Persona Capabilities

Each persona can:

1. **📖 Read Context**
   - Project documentation (`CLAUDE.md`, `README.md`)
   - Other personas' journals
   - Current codebase state

2. **📝 Create Work**
   - Pull requests with atomic changes
   - Journal entries documenting decisions

3. **💬 Communicate**
   - Send/receive mail messages
   - Coordinate with other personas
   - Respond to conflict reports

4. **🧪 Verify**
   - Run tests before committing
   - Check CI status
   - Validate changes match goals

---

## ⚙️ Scheduler

The scheduler uses **stateless round-robin** mode (implemented in `stateless.py`).

### Round-Robin Mode

**How it works:**

1. Each tick, the scheduler queries the Jules API for the last persona that ran
2. Picks the next persona alphabetically (wrapping around)
3. Only one session runs at a time — if an active session exists, the tick is skipped
4. PRs target the `jules` branch
5. Completed PRs are auto-merged before creating new sessions

```
absolutist → artisan → bdd_specialist → builder → essentialist →
evaluator → forge → lore → maya → meta → sapper → scribe →
sentinel → shepherd → streamliner → visionary → (wrap around)
```

Note: Oracle (`scheduled: false`) and Franklin (human, no prompt) are not in the rotation.

### Oracle Facilitator

Before scheduling a new persona, the scheduler runs a priority workflow:

1. **Unblock stuck sessions** — finds sessions in `AWAITING_USER_FEEDBACK` or `AWAITING_PLAN_APPROVAL` and sends guidance via a dedicated Oracle session
2. **Merge completed PRs** — auto-merges Jules draft PRs
3. **Create new session** — round-robin to the next persona

### Decommissioning a Persona

To remove a persona from the rotation, move its folder out of `.team/personas/` (e.g. to a backup location). The scheduler discovers personas by scanning for directories containing `prompt.md.j2` or `prompt.md`. No configuration file is needed.

---

## 🔧 Configuration

### Environment Variables

```bash
# ===== Required =====
export JULES_API_KEY="your-jules-api-key"
export GITHUB_TOKEN="your-github-token"

# ===== Optional =====
export JULES_BASE_URL="https://jules.googleapis.com/v1alpha"
export GH_TOKEN="your-github-token"  # Alias for GITHUB_TOKEN

# Mail backend (local or S3)
export JULES_MAIL_STORAGE="local"  # or "s3"
export JULES_MAIL_BUCKET="jules-mail"
export AWS_S3_ENDPOINT_URL="https://s3.your-provider.example"

# Persona identity (for session toolkit)
export JULES_PERSONA="weaver@team"

# Local development
export PYTHONPATH=".team"
```

### Scheduler Configuration

The scheduler is **zero-config**. It discovers personas automatically from the `.team/personas/` directory. No `schedules.toml` or configuration file is needed.

To control which personas run, simply add or remove persona directories.

---

## 📚 Usage Guide

### Command Line Interface

#### Scheduler Commands

```bash
# ===== Round-Robin Scheduler =====

# Execute one tick (recommended for CI)
uv run jules schedule tick

# Dry run (show what would execute)
uv run jules schedule tick --dry-run

# ===== Auto-Fix =====

# Analyze a specific PR for auto-fix
uv run jules autofix analyze 1234

# Run auto-fix for all failed PRs
uv run jules autofix run

# ===== Feedback Loop =====

# Check for persona feedback needs
uv run jules feedback loop

# Dry run (no API calls)
uv run jules feedback loop --dry-run

# ===== Branch Sync =====

# Sync jules -> main (no PR, direct merge)
uv run jules sync merge-main

# Rotate drifted jules branch
uv run jules sync rotate-branch
```

#### Mail Commands

```bash
# ===== Inbox Management =====

# View inbox for a persona
uv run mail inbox --persona curator@team

# View unread only
uv run mail inbox --persona curator@team --unread

# ===== Sending Messages =====

# Send a message
uv run mail send \
  --to curator@team \
  --subject "Conflict in PR #123" \
  --body "Your PR conflicts with refactor's work. Please rebase."

# Send with attachment
uv run mail send \
  --to curator@team \
  --subject "Review needed" \
  --body "See attached patch" \
  --attachment /tmp/fix.patch

# ===== Reading Messages =====

# Read specific message
uv run mail read <message-id> --persona curator@team

# Mark message as read
uv run mail mark-read <message-id> --persona curator@team
```

#### Session Toolkit (my-tools)

```bash
# ===== Authentication =====

# Login as persona
uv run my-tools login \
  --user weaver@team \
  --password "<uuidv5>" \
  --goals "Fix failing CI"

# ===== Email =====

# Check inbox
uv run my-tools email inbox --persona weaver@team

# Send email
uv run my-tools email send \
  --to curator@team \
  --subject "Status Update" \
  --body "Fixed the issue"

# ===== Journal =====

# Write journal entry
uv run my-tools journal \
  --content "Fixed CI by updating test fixtures" \
  --password "<uuidv5>"
```

### CI Integration

#### GitHub Actions Workflow

The scheduler runs automatically via `.github/workflows/jules_scheduler.yml`:

```yaml
name: Jules Scheduler

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:  # Manual trigger

  # Auto-trigger on CI success for jules-sched-* branches
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches:
      - 'jules-sched-*'

jobs:
  schedule:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run scheduler tick
        env:
          JULES_API_KEY: ${{ secrets.JULES_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PYTHONPATH: .team
        run: |
          uv run jules schedule tick
```

#### Monitoring

Check scheduler status:

```bash
# View recent workflow runs
gh run list --workflow=jules_scheduler.yml --limit 10

# View specific run
gh run view <run-id>

# View logs
gh run view <run-id> --log
```

### Local Development

#### Testing Personas Locally

```bash
# 1. Set up environment
export JULES_API_KEY="your-key"
export GITHUB_TOKEN="your-token"
export PYTHONPATH=".team"

# 2. Test persona loading
python3 << 'PYTHON_EOF'
from repo.scheduler.loader import PersonaLoader
from pathlib import Path

loader = PersonaLoader(Path('.team/personas'), {})
personas = loader.load_personas(['personas/curator/prompt.md.j2'])

print(f"Loaded: {personas[0].id} {personas[0].emoji}")
print(f"Description: {personas[0].description}")
PYTHON_EOF

# 3. Dry run scheduler
uv run jules schedule tick --dry-run
```

#### Debugging

```bash
# Enable verbose logging
export JULES_LOG_LEVEL=DEBUG
uv run jules schedule tick

# Test mail backend
python3 << 'PYTHON_EOF'
from repo.features.mail.backend import send_message, get_inbox

# Send test message
send_message(
    from_persona="test@team",
    to_persona="curator@team",
    subject="Test",
    body="Hello!"
)

# Read inbox
messages = get_inbox("curator@team", unread_only=True)
print(f"Unread: {len(messages)}")
PYTHON_EOF
```

---

## 🛠️ Persona Development

### Creating a New Persona

**Step 1: Create Directory Structure**

```bash
mkdir -p .team/personas/my_persona/journals
touch .team/personas/my_persona/prompt.md.j2
```

**Step 2: Write Persona Definition**

```jinja
---
id: my_persona
emoji: 🎯
description: "Brief description of persona role"
hired_by: your_name
---

{% extends "base/persona.md.j2" %}

{% block role %}
Your clear, concise role description.
{% endblock %}

{% block goal %}
What this persona aims to achieve.
{% endblock %}

{% block context %}
**Key Resources:**
- Reference documentation
- Related code locations
- Important patterns to follow

**Coordination:**
- Works with: Other relevant personas
- Depends on: Prerequisites
- Blocks: What depends on this persona
{% endblock %}

{% block constraints %}
- Constraint 1
- Constraint 2
- Constraint 3
{% endblock %}

{% block guardrails %}
**✅ Always:**
- Do this
- Do that
- Check this

**🚫 Never:**
- Don't do this
- Don't do that
- Avoid this
{% endblock %}

{% block output %}
{% include "blocks/pr_format.md.j2" %}
{% endblock %}

{% block verification %}
- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated
{% endblock %}
```

**Step 3: Test Locally**

The scheduler automatically discovers any persona directory with a `prompt.md.j2` file. No configuration file changes are needed.

**Step 4: Verify**

```bash
# Dry run
uv run jules schedule tick --dry-run
```

### Persona Best Practices

#### 1. Clear, Specific Instructions

```markdown
❌ Bad:
"Improve the code quality"

✅ Good:
"Identify functions with cyclomatic complexity >10 and refactor them into
smaller, testable units. Focus on src/egregora/agents/ first."
```

#### 2. Use Journal Context

```jinja
{% block context %}
**Previous Work:**
{{ journal_entries }}

**Avoid:**
- Repeating work from previous sessions
- Contradicting earlier decisions (document why if needed)
{% endblock %}
```

#### 3. Coordinate with Other Personas

```markdown
## Coordination

**Depends on:**
- Artisan completing code quality fixes
- Sentinel finishing security audit

**Blocks:**
- Forge needs UX improvements before implementation
- Scribe waits for API docs

**Collaborates with:**
- Curator on UX vision
- Janitor on code cleanup
```

#### 4. Define Success Clearly

```markdown
## Success Criteria

✅ **This session succeeds when:**
- [ ] Test coverage for agents/ reaches 80%
- [ ] All security vulnerabilities (CVSS ≥7) are fixed
- [ ] Performance regression tests added for slow queries

🚫 **This session fails if:**
- Breaking changes introduced
- CI broken for >24 hours
- Security issues ignored
```

#### 5. Celebrate "Nothing to Do"

```markdown
If there's genuinely nothing to do this session, that's SUCCESS! Document:

1. What you checked
2. Why there's no work
3. What changed since last session
4. When you'll check again

Then create a PR updating your journal with this status.
```

### Template Inheritance

Personas use Jinja2 template inheritance:

```
base/persona.md.j2               # Base template
├── blocks/pr_format.md.j2       # PR format instructions
├── blocks/testing.md.j2         # Testing guidelines
└── partials/tools.md.j2         # Available tools

personas/curator/prompt.md.j2    # Extends base, includes blocks
```

**Available Variables:**

- `{{ id }}` - Persona identifier (e.g., "curator")
- `{{ emoji }}` - Persona emoji (e.g., "🎭")
- `{{ description }}` - Persona description
- `{{ journal_entries }}` - Aggregated journal content
- `{{ password }}` - UUIDv5 derived from persona ID

**Custom Blocks:**

```jinja
{% block custom_section %}
## My Custom Section

Content here...
{% endblock %}
```

---

## 🏗️ Architecture

### Component Overview

```
┌──────────────────────────────────────────────────────────┐
│                    CLI Layer                             │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐                 │
│  │  jules  │  │  mail   │  │ my-tools │                 │
│  └────┬────┘  └────┬────┘  └────┬─────┘                 │
└───────┼────────────┼────────────┼───────────────────────┘
        │            │            │
┌───────┼────────────┼────────────┼───────────────────────┐
│       ↓            ↓            ↓         Feature Layer │
│  ┌─────────┐  ┌────────┐  ┌──────────┐                 │
│  │Scheduler│  │  Mail  │  │ Sessions │                 │
│  └────┬────┘  └────┬───┘  └────┬─────┘                 │
│  ┌─────────┐  ┌────────┐                               │
│  │ Autofix │  │Feedback│                               │
│  └────┬────┘  └────┬───┘                               │
└───────┼────────────┼───────────────────────────────────┘
        │            │            │
┌───────┼────────────┼────────────┼───────────────────────┐
│       ↓            ↓            ↓           Core Layer  │
│  ┌──────────────────────────────────────┐               │
│  │         Jules API Client             │               │
│  └──────────────────────────────────────┘               │
│  ┌──────────────────────────────────────┐               │
│  │        GitHub API Client             │               │
│  └──────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────┘
```

### Scheduler Architecture

The scheduler is implemented in `.team/repo/scheduler/stateless.py` as a single `run_scheduler()` function:

```python
# ===== Entry Point (.team/repo/scheduler/stateless.py) =====
def run_scheduler(dry_run: bool = False) -> SchedulerResult:
    """Main scheduler — stateless round-robin with Oracle facilitator.

    Priority order:
    1. Unblock stuck sessions (AWAITING_USER_FEEDBACK) via Oracle
    2. Merge completed Jules PRs
    3. Skip if active session exists
    4. Check CI status (informational)
    5. Create new session (round-robin)
    """
    ...

def discover_personas() -> list[str]:
    """Scan .team/personas/ for dirs with prompt.md.j2 or prompt.md."""
    ...

def get_next_persona(last: str | None, personas: list[str]) -> str | None:
    """Get next persona in alphabetical round-robin order."""
    ...

# ===== Loading (.team/repo/scheduler/loader.py) =====
class PersonaLoader:
    """Load and render persona Jinja2 templates."""

    def load_personas(self, paths: list[str]) -> list[PersonaConfig]:
        """Load personas from prompt files."""
        ...

# ===== Models (.team/repo/scheduler/models.py) =====
@dataclass
class PersonaConfig:
    """Immutable persona configuration."""
    id: str
    emoji: str
    description: str
    prompt_body: str
    prompt_path: Path
```

### Mail System Architecture

```python
# ===== Backend (.team/repo/features/mail/backend.py) =====
@dataclass
class Message:
    """Mail message"""
    id: str
    from_persona: str
    to_persona: str
    subject: str
    body: str
    timestamp: datetime
    read: bool
    attachments: list[str]

class MailBackend:
    """Append-only JSONL mail storage"""

    def send(self, msg: Message) -> None:
        """Append message to events.jsonl"""
        ...

    def get_inbox(self, persona: str, unread_only: bool = False) -> list[Message]:
        """Query inbox using Ibis + DuckDB"""
        ...

    def mark_read(self, persona: str, message_id: str) -> None:
        """Mark message as read (append read event)"""
        ...

# ===== Storage Backends =====
class LocalMailBackend(MailBackend):
    """Local filesystem storage"""
    storage_path = Path(".team/mail/events.jsonl")

class S3MailBackend(MailBackend):
    """S3-compatible storage"""
    bucket = os.getenv("JULES_MAIL_BUCKET")
    endpoint = os.getenv("AWS_S3_ENDPOINT_URL")
```

### Design Principles

1. **Separation of Concerns**
   - Each class has a single, well-defined responsibility
   - Managers handle specific domains (Git, GitHub, State)
   - Clear boundaries between layers

2. **Type Safety**
   - Dataclasses for all domain models
   - Type hints throughout
   - MyPy strict mode enabled

3. **Testability**
   - Dependency injection for external services
   - Protocol-based interfaces
   - Easy to mock and unit test

4. **Persistence**
   - JSONL for append-only logs (mail events)
   - Git for version control (journals, plans)

5. **Error Handling**
   - Custom exception hierarchy
   - Graceful degradation
   - Retry logic for transient failures

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Scheduler Not Advancing

**Symptom:** Same persona runs repeatedly, never advances to next persona

**Causes:**

- PRs not merging (CI failures)
- Active session still running (scheduler waits)
- Jules API not returning session history

**Solutions:**

```bash
# Check PR status
gh pr list --head jules

# Check CI status
gh pr checks <pr-number>

# Run a dry-run tick to see what would happen
uv run jules schedule tick --dry-run
```

#### 2. Session Stuck

**Symptom:** Session shows "awaiting feedback" or "awaiting approval"

**Causes:**

- Session requires human approval
- Session hit timeout
- Session waiting for input

**Solutions:**

```bash
# Check session status via Jules API
python3 << 'PYTHON_EOF'
from repo.core.client import JulesClient
client = JulesClient()
session = client.get_session("<session-id>")
print(f"Status: {session['status']}")
print(f"State: {session['state']}")
PYTHON_EOF

# Send approval (if needed)
# Note: Scheduler should auto-approve, but manual override:
# Use Jules web UI to approve plan

# Send nudge message
uv run jules feedback send-nudge <session-id>

# Cancel and restart
# (Manual via Jules UI)
```

#### 3. Branch Conflicts

**Symptom:** `jules` branch has conflicts with `main`

**Causes:**

- Drift between branches
- Manual commits to `main`
- Failed merge attempts

**Solutions:**

```bash
# Check drift
git log main..team --oneline

# Option 1: Rotate branch (preserves history)
uv run jules sync rotate-branch

# Option 2: Sync branch (rebases on main)
uv run jules sync merge-main

# Option 3: Manual resolution
git checkout jules
git pull origin main
# Resolve conflicts
git add .
git commit
git push
```

#### 4. Failed CI

**Symptom:** PR created but CI fails

**Causes:**

- Test failures
- Linting errors
- Type errors
- Security vulnerabilities

**Solutions:**

```bash
# Check CI logs
gh pr checks <pr-number>

# Option 1: Let auto-fix handle it
uv run jules autofix analyze <pr-number>

# Option 2: Manual fix
git checkout jules-sched-<persona>
# Fix issues
git commit -am "fix: address CI failures"
git push

# Option 3: Close PR and continue
gh pr close <pr-number>
uv run jules schedule tick  # Moves to next persona
```

#### 5. Mail System Issues

**Symptom:** Personas not receiving messages

**Causes:**

- Mail backend not initialized
- Incorrect persona ID format
- Storage backend misconfigured

**Solutions:**

```bash
# Check mail backend
ls -la .team/mail/

# Test mail system
python3 << 'PYTHON_EOF'
from repo.features.mail.backend import send_message, get_inbox

# Send test
send_message(
    from_persona="test@team",
    to_persona="curator@team",
    subject="Test",
    body="Hello"
)

# Check inbox
messages = get_inbox("curator@team")
print(f"Messages: {len(messages)}")
PYTHON_EOF

# Verify persona ID format
# Should be: <persona-id>@team
# NOT: <persona-id> or <persona-id>@domain
```

#### 6. Template Rendering Errors

**Symptom:** "Template not found" or Jinja2 errors

**Causes:**

- Missing base templates
- Incorrect template syntax
- Missing template variables

**Solutions:**

```bash
# Check template exists
ls -la .team/repo/templates/base/persona.md.j2

# Test template rendering
python3 << 'PYTHON_EOF'
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

env = Environment(loader=FileSystemLoader([
    '.team/repo/templates',
    '.team/personas',
]))

template = env.get_template('curator/prompt.md.j2')
rendered = template.render(
    id='curator',
    emoji='🎭',
    description='Test',
    journal_entries='',
    password='test-uuid',
)
print(rendered[:200])
PYTHON_EOF
```

### Debug Mode

Enable verbose logging:

```bash
# Set log level
export JULES_LOG_LEVEL=DEBUG

# Run with verbose output
uv run jules schedule tick 2>&1 | tee scheduler.log

# Check logs
tail -f scheduler.log
```

### Health Checks

```bash
# Check scheduler health
uv run jules schedule status

# Check all open PRs
gh pr list --head jules

# Check recent workflow runs
gh run list --workflow=jules_scheduler.yml --limit 5

# Check mail system
uv run mail inbox --persona system@team
```

---

## 📚 Resources

### Internal Documentation

- **[CLAUDE.md](../CLAUDE.md)** - Coding standards and contribution guidelines
- **[README.md](../README.md)** - Project overview
- **[PARALLEL_PERSONAS_README.md](./PARALLEL_PERSONAS_README.md)** - Parallel execution design
- **[PARALLEL_PERSONAS_PROMPT.md](./PARALLEL_PERSONAS_PROMPT.md)** - Implementation prompt
- **[SESSION_ID_PATTERNS.md](./SESSION_ID_PATTERNS.md)** - Session ID extraction logic
- **[API_COMPLIANCE_REVIEW.md](./API_COMPLIANCE_REVIEW.md)** - API compliance notes

### External Resources

- **[Jules Documentation](https://developers.google.com/jules)** - Jules API reference
- **[GitHub CLI](https://cli.github.com/)** - GitHub CLI documentation
- **[Jinja2 Templates](https://jinja.palletsprojects.com/)** - Template syntax reference
- **[Cron Expression](https://crontab.guru/)** - Cron expression tester

### Getting Help

- **GitHub Issues** - Report bugs or request features
- **GitHub Discussions** - Ask questions or share ideas
- **Persona Journals** - Review past work for context

---

## 🔄 Changelog

### 2026-01-30

- **Persona count**: 18 (17 AI + 1 human), down from 21
- **Cut**: Bolt (perf), Deps (dependency mgmt), Janitor (cleanup), Curator (UX eval)
- **Merged**: Janitor (code cleanup) and Curator (UX evaluation) duties absorbed into Forge
- **Forge** is now a full-stack implementer: features + UX evaluation + code cleanup
- **Scheduler**: frontmatter-based `scheduled: false` opt-out replaces hardcoded exclusion list
- **Oracle**: prompt loaded from disk instead of hardcoded string

### 2026-01-29

- **Persona count**: 21 (20 AI + 1 human), down from 23
- **Eliminated**: Typeguard, Sheriff, Simplifier, Organizer, Refactor (consolidated into other personas)
- **Added**: Deps (dependency management), Meta (system introspection), Franklin (human project lead)
- **Framework**: Restructured base template from RGCCOV to **ROSAV** (Role, Objective, Situation, Act, Verify)
- **Collaboration**: Strengthened my-tools email nudges; login now shows unread email notification panel
- **Self-improvement**: Personas now see exact paths to their prompt and must journal before editing

### 2026-01-20

- **Persona consolidation**: Reduced from 28 to 23 personas
- **Eliminated**: Steward, Maintainer, Taskmaster, Pruner, Palette, Docs Curator (redundant roles)
- **Rewrote Oracle**: Now a support agent who unblocks personas with technical guidance
- **Rewrote Visionary**: Added mandatory 5-step inspiration process + BDD acceptance criteria in RFCs
- **Improved Scribe**: Absorbed docs_curator, now handles both creation and maintenance
- **Removed eliminated personas** from `.team/personas/`

### 2026-01-17

- Comprehensive README overhaul
- Added visual diagrams and examples
- Expanded troubleshooting section
- Enhanced persona development guide
- Added architecture deep dive

### 2026-01-14

- Updated persona count to 28
- Added new personas (absolutist, bdd_specialist, oracle, etc.)
- Improved scheduler architecture docs

### 2026-01-09

- Original README created
- Basic scheduler and persona documentation
- Initial usage guide

---

**Maintained by:** Weaver persona 🕸️ and human contributors
**Last Updated:** 2026-01-29
**Version:** 3.0
