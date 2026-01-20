# 🤖 Jules Automation System

> Autonomous AI agents working together to maintain, improve, and evolve the CausaGanha codebase

## 📖 Table of Contents

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [Directory Structure](#-directory-structure)
- [Personas](#-personas)
- [Scheduler Modes](#-scheduler-modes)
- [Sprint System](#-sprint-system)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Persona Development](#-persona-development)
- [Architecture](#-architecture)
- [Troubleshooting](#-troubleshooting)
- [Resources](#-resources)

---

## 🎯 Overview

The Jules automation system is a **multi-agent AI workforce** that maintains and improves the CausaGanha codebase autonomously. Each agent (persona) has a specialized role and works independently or collaboratively through a sophisticated scheduler.

### Key Features

- **10 Specialized Personas** - Tailored for legal data platform (security, testing, architecture, etc.)
- **Autonomous Operation** - Agents create PRs, review code, and coordinate work
- **Sprint-Based Planning** - Personas plan ahead and provide feedback to each other
- **Multiple Execution Modes** - Parallel cycles, scheduled runs, and on-demand execution
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
│  │ Curator  │→ │ Refactor │→ │ Visionary│→ │   Bolt   │   │
│  │    🎭    │  │    🔧    │  │    🔮    │  │    ⚡    │   │
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

### Run a Single Persona

```bash
# Run the curator persona
uv run jules schedule tick --prompt-id curator

# Dry run (see what would happen)
uv run jules schedule tick --prompt-id curator --dry-run
```

### Run the Parallel Cycle

```bash
# Execute one tick of the parallel cycle
uv run jules schedule tick

# Run all personas (ignore schedules)
uv run jules schedule tick --all
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
│   │   ├── sessions/          # Session management
│   │   └── sprints/           # Sprint planning
│   ├── scheduler/              # Scheduler engine
│   │   ├── engine.py          # Main scheduler logic
│   │   ├── loader.py          # Persona loading
│   │   ├── managers.py        # Branch, PR, State managers
│   │   ├── models.py          # Data models
│   │   └── state.py           # Persistent state
│   └── templates/              # Jinja2 templates
│       ├── base/              # Base templates
│       ├── blocks/            # Reusable blocks
│       └── partials/          # Partial templates
│
├── personas/                   # AI agent definitions (23 personas)
│   ├── absolutist/            # 🎯 Strict rule enforcement
│   ├── artisan/               # 🔨 Code craftsmanship
│   ├── bdd_specialist/        # 🧪 BDD testing expert
│   ├── bolt/                  # ⚡ Performance optimization
│   ├── builder/               # 🏗️ Data architecture
│   ├── curator/               # 🎭 UX/UI evaluation
│   ├── essentialist/          # 💎 Pragmatic cuts
│   ├── forge/                 # ⚒️ Feature implementation
│   ├── janitor/               # 🧹 Code hygiene
│   ├── lore/                  # 📚 System historian
│   ├── oracle/                # 🔮 Support agent
│   ├── organizer/             # 🗂️ Project organization
│   ├── refactor/              # 🔧 Code quality
│   ├── sapper/                # 💣 Exception structuring
│   ├── scribe/                # ✍️ Documentation
│   ├── sentinel/              # 🛡️ Security audits
│   ├── shepherd/              # 🧑‍🌾 Test coverage
│   ├── sheriff/               # 🤠 Test stability
│   ├── simplifier/            # 📉 Complexity reduction
│   ├── streamliner/           # 🌊 Data optimization
│   ├── typeguard/             # 🔍 Type safety
│   ├── visionary/             # 🔭 Strategic RFCs
│   └── _archived/             # Eliminated personas
│
├── mail/                       # Mail system storage
│   └── events.jsonl           # Mail event log
│
├── state/                      # Scheduler state
│   ├── cycle_state.json       # Current cycle position
│   └── reconciliation/        # PR reconciliation data
│
├── sprints/                    # Sprint planning
│   ├── current.txt            # Current sprint number
│   ├── sprint-1/              # Sprint 1 plans
│   ├── sprint-2/              # Sprint 2 plans
│   └── ...
│
├── schedules.toml             # Scheduler configuration
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
- **Sprint planning** capability for coordination
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
- Edit templates in src/egregora/output_adapters/mkdocs/
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

| Emoji | Name | Role | Focus Area |
| :---: | :--- | :--- | :--- |
| 🎯 | **Absolutist** | Rule Enforcer | Strict standards enforcement |
| 🔨 | **Artisan** | Craftsman | Code quality and refactoring |
| 🧪 | **BDD Specialist** | Test Expert | Behavior-driven testing |
| ⚡ | **Bolt** | Perf. Engineer | Performance optimization |
| 🏗️ | **Builder** | Architect | Data architecture, schemas |
| 🎭 | **Curator** | UX Designer | User experience, blog evaluation |
| 💎 | **Essentialist** | Pragmatist | Strategic cuts, focus |
| ⚒️ | **Forge** | Builder | Feature implementation |
| 🧹 | **Janitor** | Hygienist | Code cleanup, technical debt |
| 📚 | **Lore** | Historian | System history, ADRs, git forensics |
| 🔮 | **Oracle** | Support Agent | Unblock personas with technical guidance |
| 🗂️ | **Organizer** | Maintainer | Project structure |
| 🔧 | **Refactor** | Developer | Linting, TDD-based fixes |
| 💣 | **Sapper** | Structurer | Exception handling patterns |
| ✍️ | **Scribe** | Writer | Documentation creation & maintenance |
| 🛡️ | **Sentinel** | Security | Vulnerability scanning |
| 🧑‍🌾 | **Shepherd** | Test Engineer | Test coverage expansion |
| 🤠 | **Sheriff** | Build Cop | Test stability, flake fixes |
| 📉 | **Simplifier** | Reducer | Complexity reduction |
| 🌊 | **Streamliner** | Optimizer | Data processing efficiency |
| 🔍 | **Typeguard** | Type Checker | Type safety enforcement |
| 🔭 | **Visionary** | Strategist | Strategic RFCs with BDD criteria |

### Persona Capabilities

Each persona can:

1. **📖 Read Context**
   - Project documentation (`CLAUDE.md`, `README.md`)
   - Other personas' journals
   - Sprint plans and feedback
   - Current codebase state

2. **📝 Create Work**
   - Pull requests with atomic changes
   - Journal entries documenting decisions
   - Sprint plans for future work
   - Feedback on other personas' plans

3. **💬 Communicate**
   - Send/receive mail messages
   - Coordinate with other personas
   - Respond to conflict reports

4. **🧪 Verify**
   - Run tests before committing
   - Check CI status
   - Validate changes match goals

---

## ⚙️ Scheduler Modes

The scheduler supports two execution modes: **Parallel Cycle** and **Scheduled**.

### 1. Parallel Cycle Mode

**Sequential execution within tracks, parallel across tracks**

```
Track 1:  curator → refactor → visionary → bolt
            ↓         ↓          ↓         ↓
          PR #1     PR #2      PR #3     PR #4

Track 2:  sentinel → builder → shepherd
            ↓          ↓         ↓
          PR #5      PR #6     PR #7
```

**How it works:**

1. Scheduler loads tracks from `schedules.toml`
2. Each track runs personas sequentially
3. A persona waits for the previous session to finish
4. PRs target the `jules` branch
5. State persists in `.team/state/cycle_state.json`
6. Auto-merge happens when CI passes

**Benefits:**

- ✅ No merge conflicts (sequential within track)
- ✅ Each persona builds on previous work
- ✅ Sprint-based organization
- ✅ Predictable execution order

**Configuration:**

```toml
# schedules.toml
[tracks]
default = [
    "personas/curator/prompt.md.j2",
    "personas/refactor/prompt.md.j2",
    "personas/visionary/prompt.md.j2",
]

ops = [
    "personas/sentinel/prompt.md.j2",
    "personas/sheriff/prompt.md.j2",
]
```

### 2. Scheduled Mode

**Independent cron-based execution**

```toml
# schedules.toml
[schedules]
simplifier = "0 */2 * * *"    # Every 2 hours
organizer = "0 * * * *"        # Hourly
curator = "0 0 * * *"          # Daily at midnight UTC
```

**How it works:**

1. Scheduler checks current time every tick
2. Runs any persona matching its cron schedule
3. Creates PRs targeting `main` directly
4. Personas run independently (no coordination)

**Cron Format:**

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

**Common Examples:**

- `0 * * * *` - Every hour
- `*/15 * * * *` - Every 15 minutes
- `0 0 * * *` - Daily at midnight
- `0 0 * * 1` - Every Monday at midnight
- `0 9-17 * * 1-5` - Weekdays 9 AM - 5 PM

**Benefits:**

- ✅ Run personas at optimal times
- ✅ Independent operation
- ✅ Predictable resource usage

---

## 📅 Sprint System

Sprints organize work into cycles, providing context and continuity across personas.

### Sprint Structure

```
.team/sprints/
├── current.txt              # Contains: "42"
├── sprint-41/
│   ├── curator-plan.md      # Curator's plan for sprint 41
│   ├── refactor-plan.md     # Refactor's plan for sprint 41
│   └── visionary-feedback.md # Visionary's feedback on others' plans
├── sprint-42/               # Current sprint
│   ├── curator-plan.md
│   ├── refactor-plan.md
│   ├── sentinel-plan.md
│   └── ...
└── sprint-43/               # Next sprint (planning ahead)
    ├── curator-plan.md
    └── ...
```

### Sprint Flow

```
┌─────────────────────────────────────────────────────────┐
│  Sprint N-1 (Past)                                      │
│  └─ Completed work, archived journals                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Sprint N (Current)                                     │
│  ├─ Active work                                         │
│  ├─ Personas execute their plans                       │
│  └─ Create PRs and journal entries                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Sprint N+1 (Next)                                      │
│  ├─ Personas write plans                               │
│  ├─ Personas review others' plans                      │
│  └─ Personas provide feedback                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Sprint N+2 (Future)                                    │
│  └─ Early planning and coordination                    │
└─────────────────────────────────────────────────────────┘
```

### Sprint Context in Prompts

Every persona receives:

```jinja
## 📅 Sprint Context

**Current Sprint:** {{ current_sprint }}
**Your Plan:** See sprints/sprint-{{ current_sprint }}/{{ id }}-plan.md
**Others' Plans:** See sprints/sprint-{{ current_sprint }}/*-plan.md
**Feedback:** See sprints/sprint-{{ current_sprint }}/*-feedback.md

### Your Responsibilities

1. **Execute** your plan for sprint {{ current_sprint }}
2. **Plan** your work for sprint {{ current_sprint + 1 }}
3. **Review** other personas' plans and provide feedback
4. **Coordinate** with personas working on related areas
```

### Plan Template

```markdown
# Sprint {{ sprint_number }} Plan - {{ persona_name }}

## Goals
- [ ] Goal 1: Brief description
- [ ] Goal 2: Brief description
- [ ] Goal 3: Brief description

## Context
Why these goals matter...

## Dependencies
- Depends on Refactor completing X
- Blocks Palette from starting Y

## Success Criteria
- Specific, measurable outcomes
- Test coverage targets
- Performance benchmarks

## Risks
- Potential blockers
- Mitigation strategies
```

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

### schedules.toml

Complete configuration example:

```toml
# ===== Parallel Cycle Mode =====
[tracks]

# Main development track
default = [
    "personas/curator/prompt.md.j2",
    "personas/refactor/prompt.md.j2",
    "personas/visionary/prompt.md.j2",
    "personas/bolt/prompt.md.j2",
    "personas/sentinel/prompt.md.j2",
    "personas/builder/prompt.md.j2",
    "personas/shepherd/prompt.md.j2",
]

# Operations track (runs in parallel with default)
ops = [
    "personas/janitor/prompt.md.j2",
    "personas/sheriff/prompt.md.j2",
]

# Documentation track
docs = [
    "personas/scribe/prompt.md.j2",
    "personas/docs_curator/prompt.md.j2",
]

# ===== Scheduled Mode =====
[schedules]

# Hourly maintenance
organizer = "0 * * * *"
pruner = "30 * * * *"

# Every 2 hours
simplifier = "0 */2 * * *"
streamliner = "15 */2 * * *"

# Daily at midnight UTC
palette = "0 0 * * *"
essentialist = "0 1 * * *"

# Weekdays only
taskmaster = "0 9 * * 1-5"  # 9 AM Mon-Fri
```

---

## 📚 Usage Guide

### Command Line Interface

#### Scheduler Commands

```bash
# ===== Parallel Cycle =====

# Execute one tick (recommended for CI)
uv run jules schedule tick

# Run specific persona only
uv run jules schedule tick --prompt-id curator

# Run all personas (ignore schedules)
uv run jules schedule tick --all

# Dry run (show what would execute)
uv run jules schedule tick --dry-run

# Force specific mode
uv run jules schedule tick --mode cycle    # Parallel cycle
uv run jules schedule tick --mode scheduled  # Cron-based

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

# 4. Run specific persona
uv run jules schedule tick --prompt-id curator
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

**Step 3: Add to Schedule**

```toml
# schedules.toml

# Option A: Add to cycle track
[tracks]
default = [
    # ... existing personas
    "personas/my_persona/prompt.md.j2",
]

# Option B: Add cron schedule
[schedules]
my_persona = "0 6 * * *"  # Daily at 6 AM
```

**Step 4: Test Locally**

```bash
# Dry run
uv run jules schedule tick --prompt-id my_persona --dry-run

# Actual run
uv run jules schedule tick --prompt-id my_persona
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
- Repeating work from previous sprints
- Contradicting earlier decisions (document why if needed)
{% endblock %}
```

#### 3. Coordinate with Other Personas

```markdown
## Coordination

**Depends on:**
- Refactor completing linting fixes
- Sentinel finishing security audit

**Blocks:**
- Palette needs UX improvements before design work
- Scribe waits for API docs

**Collaborates with:**
- Curator on UX vision
- Janitor on code cleanup
```

#### 4. Define Success Clearly

```markdown
## Success Criteria

✅ **This sprint succeeds when:**
- [ ] Test coverage for agents/ reaches 80%
- [ ] All security vulnerabilities (CVSS ≥7) are fixed
- [ ] Performance regression tests added for slow queries

🚫 **This sprint fails if:**
- Breaking changes introduced
- CI broken for >24 hours
- Security issues ignored
```

#### 5. Celebrate "Nothing to Do"

```markdown
If there's genuinely nothing to do this sprint, that's SUCCESS! Document:

1. What you checked
2. Why there's no work
3. What changed since last sprint
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
- `{{ sprint_context_text }}` - Current sprint context
- `{{ current_sprint }}` - Current sprint number

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
│  ┌─────────┐  ┌────────┐  ┌──────────┐                 │
│  │ Autofix │  │Feedback│  │ Sprints  │                 │
│  └────┬────┘  └────┬───┘  └────┬─────┘                 │
└───────┼────────────┼────────────┼───────────────────────┘
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

```python
# ===== Domain Models (.team/repo/scheduler/models.py) =====
@dataclass
class PersonaConfig:
    """Immutable persona configuration"""
    id: str
    emoji: str
    description: str
    prompt_content: str
    prompt_path: Path

@dataclass
class CycleState:
    """Current position in cycle"""
    track_name: str
    current_index: int
    session_id: str | None
    last_pr_number: int | None

@dataclass
class SessionRequest:
    """Session creation parameters"""
    persona_config: PersonaConfig
    branch: str
    title: str
    automation_mode: str

@dataclass
class PRStatus:
    """PR status with CI checks"""
    number: int
    state: str
    mergeable: bool
    ci_passing: bool
    checks: list[dict]

# ===== Loading (.team/repo/scheduler/loader.py) =====
class PersonaLoader:
    """Load and parse persona definitions"""

    def load_personas(self, paths: list[str]) -> list[PersonaConfig]:
        """Load personas from prompt files"""
        ...

    def _render_template(self, path: Path) -> str:
        """Render Jinja2 template with context"""
        ...

# ===== State (.team/repo/scheduler/state.py) =====
class PersistentCycleState:
    """JSON-backed persistent state"""

    def get_state(self, track: str) -> CycleState | None:
        """Get current state for track"""
        ...

    def update_state(self, track: str, state: CycleState) -> None:
        """Update state for track"""
        ...

    def save(self) -> None:
        """Persist to disk"""
        ...

# ===== Managers (.team/repo/scheduler/managers.py) =====
class BranchManager:
    """Git branch operations"""

    def ensure_branch_exists(self, branch: str, base: str = "main") -> None:
        """Create branch if needed"""
        ...

    def sync_branch(self, branch: str, base: str = "main") -> None:
        """Sync branch with base"""
        ...

class PRManager:
    """GitHub PR operations"""

    def get_pr_status(self, number: int) -> PRStatus:
        """Get PR status and CI checks"""
        ...

    def merge_if_ready(self, number: int) -> bool:
        """Merge PR if CI passes"""
        ...

    def list_open_prs(self, head: str) -> list[dict]:
        """List open PRs for branch"""
        ...

class CycleStateManager:
    """Cycle progression logic"""

    def should_advance(self, state: CycleState, pr_status: PRStatus) -> bool:
        """Check if cycle should advance"""
        ...

    def advance(self, track: str, personas: list[PersonaConfig]) -> CycleState:
        """Move to next persona in track"""
        ...

class SessionOrchestrator:
    """Jules session creation"""

    def create_session(self, request: SessionRequest) -> str:
        """Create new Jules session"""
        ...

    def poll_session(self, session_id: str) -> dict:
        """Check session status"""
        ...

# ===== Engine (.team/repo/scheduler/engine.py) =====
def execute_parallel_cycle_tick(
    tracks: dict[str, list[str]],
    dry_run: bool = False
) -> None:
    """Execute one tick of parallel cycle mode"""
    loader = PersonaLoader(...)
    state_manager = PersistentCycleState(...)
    pr_manager = PRManager(...)
    orchestrator = SessionOrchestrator(...)

    for track_name, persona_paths in tracks.items():
        # Load track state
        state = state_manager.get_state(track_name)

        # Load personas
        personas = loader.load_personas(persona_paths)

        # Check if should advance
        if state and state.last_pr_number:
            pr_status = pr_manager.get_pr_status(state.last_pr_number)
            if pr_manager.merge_if_ready(state.last_pr_number):
                state = cycle_manager.advance(track_name, personas)

        # Create session for current persona
        current_persona = personas[state.current_index]
        session_id = orchestrator.create_session(...)

        # Update state
        state.session_id = session_id
        state_manager.update_state(track_name, state)
        state_manager.save()

def execute_scheduled_tick(
    schedules: dict[str, str],
    dry_run: bool = False
) -> None:
    """Execute scheduled persona runs"""
    loader = PersonaLoader(...)
    orchestrator = SessionOrchestrator(...)

    current_time = datetime.now(UTC)

    for persona_id, cron_expr in schedules.items():
        if should_run(cron_expr, current_time):
            persona = loader.load_personas([f"personas/{persona_id}/prompt.md.j2"])[0]
            orchestrator.create_session(...)
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

### Sprint System Architecture

```python
# ===== Sprint Manager (.team/repo/features/sprints/manager.py) =====
class SprintManager:
    """Sprint planning and coordination"""

    def get_current_sprint(self) -> int:
        """Read current sprint number"""
        return int(Path(".team/sprints/current.txt").read_text())

    def increment_sprint(self) -> int:
        """Increment sprint and create directory"""
        current = self.get_current_sprint()
        next_sprint = current + 1
        Path(f".team/sprints/sprint-{next_sprint}").mkdir(exist_ok=True)
        Path(".team/sprints/current.txt").write_text(str(next_sprint))
        return next_sprint

    def get_sprint_context(self, persona_id: str) -> dict:
        """Load sprint plans and feedback for persona"""
        current = self.get_current_sprint()

        return {
            "current_sprint": current,
            "my_plan": self._load_plan(persona_id, current),
            "others_plans": self._load_all_plans(current),
            "feedback": self._load_feedback(persona_id, current),
        }

    def save_plan(self, persona_id: str, sprint: int, content: str) -> None:
        """Save persona's plan for sprint"""
        plan_file = Path(f".team/sprints/sprint-{sprint}/{persona_id}-plan.md")
        plan_file.write_text(content)

    def save_feedback(self, persona_id: str, sprint: int, content: str) -> None:
        """Save persona's feedback on others' plans"""
        feedback_file = Path(f".team/sprints/sprint-{sprint}/{persona_id}-feedback.md")
        feedback_file.write_text(content)
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
   - JSON for simple state (cycle_state.json)
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

**Symptom:** Curator persona runs repeatedly, never advances to refactor

**Causes:**

- PRs not merging (CI failures)
- PRs targeting wrong base branch
- State file corruption

**Solutions:**

```bash
# Check PR status
gh pr list --head jules

# Check CI status
gh pr checks <pr-number>

# Check state file
cat .team/state/cycle_state.json

# Reset state (DANGER: loses cycle position)
rm .team/state/cycle_state.json

# Force advance to next persona
uv run jules schedule tick --prompt-id refactor
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
git checkout jules-sched-<sprint>-<persona>
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
    sprint_context_text='Sprint 1',
    current_sprint=1,
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

### 2026-01-20

- **Persona consolidation**: Reduced from 28 to 23 personas
- **Eliminated**: Steward, Maintainer, Taskmaster, Pruner, Palette, Docs Curator (redundant roles)
- **Rewrote Oracle**: Now a support agent who unblocks personas with technical guidance
- **Rewrote Visionary**: Added mandatory 5-step inspiration process + BDD acceptance criteria in RFCs
- **Improved Scribe**: Absorbed docs_curator, now handles both creation and maintenance
- **Archived eliminated personas** to `.team/personas/_archived/`

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
**Last Updated:** 2026-01-20
**Version:** 2.1
