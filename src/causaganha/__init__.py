"""CausaGanha - Lawyer performance ratings from Brazilian judicial data."""

# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
