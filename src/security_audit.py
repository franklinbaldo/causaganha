"""Run a basic security audit using pip-audit."""

import subprocess
import sys


def run_security_audit() -> int:
    """Execute pip-audit and return the exit code."""
    try:
        result = subprocess.run(["pip-audit"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    except FileNotFoundError:
        print(
            "pip-audit is not installed. Install with 'uv pip install pip-audit'",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(run_security_audit())
