# Tools Usage Logs

This directory contains per-session tool usage logs for Jules personas.

## Directory Structure

```
.team/logs/
└── tools_use/
    ├── typeguard_025_20260117T081528.csv
    ├── builder_058_20260118T233322.csv
    ├── docs_curator_060_20260119T000156.csv
    └── forge_089_20260119T174217.csv
```

## File Naming Convention

Each log file follows the pattern:

```
{persona}_{sequence}_{timestamp}.csv
```

Where:
- **persona**: The persona ID (e.g., `typeguard`, `builder`, `maya`)
- **sequence**: The session sequence number (e.g., `025`, `058`)
- **timestamp**: Session start time in format `YYYYMMDDTHHmmss` (e.g., `20260117T081528`)

## CSV Format

Each log file contains the following columns:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp of the command execution |
| `persona` | Persona ID that executed the command |
| `sequence` | Session sequence number |
| `command` | Command name (e.g., `roster list-personas`, `email inbox`) |
| `args` | Command arguments as a string (sensitive data redacted) |

### Example

```csv
timestamp,persona,sequence,command,args
2026-01-17T08:15:28.863069,typeguard,025,login,"{'user': 'typeguard', 'password': '***', 'goals': ['First Login']}"
2026-01-17T08:16:12.167248,typeguard,025,roster list-personas,{}
2026-01-17T08:16:37.907254,typeguard,025,login,"{'user': 'typeguard', 'password': '***', 'goals': ['Second Login']}"
```

## Why Per-Session Files?

The original design used a single `tools_use.csv` file, which caused merge conflicts when multiple personas ran in parallel. The new design:

✅ **Eliminates merge conflicts** - Each session writes to its own file
✅ **Preserves complete history** - No data loss during parallel execution
✅ **Enables easier analysis** - Filter logs by persona, sequence, or date
✅ **Improves performance** - Smaller files, faster reads/writes

## Migration from Legacy

The legacy single-file log (`.team/tools_use.csv`) is deprecated but still supported for backward compatibility. The `PulseManager` reads from both:
1. New per-session logs in `.team/logs/tools_use/`
2. Legacy log file `.team/tools_use.csv` (if exists)

## Authentication Requirement

**All my-tools commands require login** (except `login` itself):

```bash
# ❌ Will fail with AuthenticationError
my-tools email inbox

# ✅ Must login first
my-tools login --user maya@team --password <token>
my-tools email inbox  # Now works
```

The `@log_tool_command` decorator enforces this requirement:
- Commands fail fast with a clear error message if not logged in
- Only the `login` command itself bypasses this check (`require_login=False`)
- Prevents logging to "unknown" persona/sequence files

## API Usage

### Logging Tool Usage

The `LogManager` automatically creates session-specific files:

```python
from repo.features.logging import log_manager

# Logs are automatically written to per-session files
log_manager.log_use(
    persona="maya",
    sequence="001",
    command_path="email inbox",
    args={"unread": True}
)
```

### Reading Logs

Use the `read_all_logs` utility to read logs across sessions:

```python
from repo.features.logging import read_all_logs

# Read all logs for a persona
logs = read_all_logs(persona="maya")

# Read all logs for all personas
all_logs = read_all_logs()
```

### Getting Last Tool Used

The `PulseManager` automatically scans all log files:

```python
from repo.features.pulse import PulseManager

pulse = PulseManager()
last_tool = pulse._get_last_tool_used("maya")
```

## Cleanup

Log files accumulate over time. Consider periodic cleanup:

```bash
# Keep only logs from last 30 days
find .team/logs/tools_use -name "*.csv" -mtime +30 -delete

# Keep only logs from last 100 sessions per persona
# (manual script needed)
```

## Ignored Files

All log files are gitignored (`.gitignore`):

```
.team/tools_use.csv    # Legacy log file
.team/logs/            # All per-session logs
```

---

**Last Updated**: 2026-01-20
**Responsible Personas**: All personas using `my-tools` commands
