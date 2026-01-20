import csv
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

LOG_FILE = Path(".team/tools_use.csv")

class LogManager:
    def __init__(self, log_file: Path = LOG_FILE):
        self.log_file = log_file

    def log_use(self, persona: Optional[str], sequence: Optional[str], command_path: str, args: Dict[str, Any]):
        """
        Logs a command execution to the CSV log file.
        """
        # Redact sensitive info
        safe_args = args.copy()
        if 'password' in safe_args:
            safe_args['password'] = '***'
        
        file_exists = self.log_file.exists()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.log_file, mode='a', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'persona', 'sequence', 'command', 'args']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'persona': persona or "unknown",
                    'sequence': sequence or "unknown",
                    'command': command_path,
                    'args': str(safe_args)
                })
        except Exception as e:
            print(f"⚠️ Warning: Could not write to log file: {e}")

def log_tool_command(prefix: str = ""):
    """Decorator to log my-tools command usage."""
    import functools
    from repo.features.session import SessionManager

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            sm = SessionManager()
            persona = sm.get_active_persona()
            sequence = sm.get_active_sequence()
            
            # Clean up command name (replace underscores with dashes for CLI feel)
            cmd_name = func.__name__.replace("_", "-")
            full_path = f"{prefix} {cmd_name}".strip()
            
            log_manager.log_use(persona, sequence, full_path, kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator

log_manager = LogManager()
