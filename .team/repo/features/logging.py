import csv
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Legacy log file (deprecated, kept for reference)
LOG_FILE = Path(".team/tools_use.csv")

# New per-session log directory
LOGS_DIR = Path(".team/logs/tools_use")

class LogManager:
    def __init__(self, log_dir: Path = LOGS_DIR):
        self.log_dir = log_dir
        self._current_session_file: Optional[Path] = None
        self._session_persona: Optional[str] = None
        self._session_sequence: Optional[str] = None
        self._session_start: Optional[datetime.datetime] = None

    def _get_session_log_file(self, persona: str, sequence: str) -> Path:
        """
        Get or create the log file for the current session.

        Format: {persona}_{sequence}_{YYYYMMDDTHHmmss}.csv
        """
        # Check if we need to create a new session file
        if (self._current_session_file is None or
            self._session_persona != persona or
            self._session_sequence != sequence):

            # Start new session
            self._session_persona = persona
            self._session_sequence = sequence
            self._session_start = datetime.datetime.now()

            timestamp = self._session_start.strftime("%Y%m%dT%H%M%S")
            filename = f"{persona}_{sequence}_{timestamp}.csv"
            self._current_session_file = self.log_dir / filename

        return self._current_session_file

    def log_use(self, persona: Optional[str], sequence: Optional[str], command_path: str, args: Dict[str, Any]):
        """
        Logs a command execution to a per-session CSV log file.

        Each session (persona + sequence) gets its own log file to avoid merge conflicts.

        Args:
            persona: Persona ID from active session (None only for login command)
            sequence: Sequence number from active session (None only for login command)
            command_path: Full command path (e.g., "login", "email inbox")
            args: Command arguments (sensitive data should be redacted by caller)

        Note:
            persona/sequence are None ONLY for the "login" command (before session is created).
            All other commands are protected by @log_tool_command(require_login=True).
        """
        # Use "unknown" for missing persona/sequence (only happens during login)
        persona = persona or "unknown"
        sequence = sequence or "unknown"

        # Redact sensitive info
        safe_args = args.copy()
        if 'password' in safe_args:
            safe_args['password'] = '***'

        # Get session-specific log file
        log_file = self._get_session_log_file(persona, sequence)

        file_exists = log_file.exists()
        log_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(log_file, mode='a', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'persona', 'sequence', 'command', 'args']
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'persona': persona,
                    'sequence': sequence,
                    'command': command_path,
                    'args': str(safe_args)
                })
        except Exception as e:
            print(f"⚠️ Warning: Could not write to log file: {e}")

def log_tool_command(prefix: str = "", require_login: bool = True):
    """Decorator to log my-tools command usage.

    Args:
        prefix: Command prefix (e.g., "email" for subcommands)
        require_login: If True, require active session before executing command.
                      Set to False only for the "login" command itself.
    """
    import functools
    from repo.core.exceptions import AuthenticationError

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from repo.features.session import SessionManager

            sm = SessionManager()
            persona = sm.get_active_persona()
            sequence = sm.get_active_sequence()

            # Clean up command name (replace underscores with dashes for CLI feel)
            cmd_name = func.__name__.replace("_", "-")
            full_path = f"{prefix} {cmd_name}".strip()

            # Check authentication requirement
            if require_login and (persona is None or sequence is None):
                raise AuthenticationError(
                    f"Authentication required to use '{full_path}'. "
                    f"Please run 'my-tools login' first."
                )

            log_manager.log_use(persona, sequence, full_path, kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

log_manager = LogManager()


def read_all_logs(persona: Optional[str] = None, log_dir: Path = LOGS_DIR) -> list[Dict[str, str]]:
    """
    Read all tool usage logs, optionally filtered by persona.

    Args:
        persona: Filter logs for specific persona (None = all personas)
        log_dir: Directory containing log files

    Returns:
        List of log entries sorted by timestamp (most recent first)
    """
    all_rows = []

    if not log_dir.exists():
        return all_rows

    try:
        # Determine pattern
        pattern = f"{persona}_*.csv" if persona else "*.csv"

        # Read all matching log files
        for log_file in log_dir.glob(pattern):
            try:
                with open(log_file, mode='r', newline='') as f:
                    reader = csv.DictReader(f)
                    all_rows.extend(list(reader))
            except Exception:
                continue  # Skip corrupted files

        # Sort by timestamp (most recent first)
        all_rows.sort(key=lambda r: r.get('timestamp', ''), reverse=True)

    except Exception as e:
        print(f"⚠️ Warning: Could not read log files: {e}")

    return all_rows
