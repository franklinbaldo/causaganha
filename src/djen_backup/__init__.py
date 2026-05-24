"""djen-backup: Complete backup of Brazil's DJEN to the Internet Archive."""


# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys
for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass

__version__ = "0.1.0"
