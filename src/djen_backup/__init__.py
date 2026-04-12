"""djen-backup: Complete backup of Brazil's DJEN to the Internet Archive."""

__version__ = "0.1.0"

from djen_backup.engine import sync_date


__all__ = ["sync_date"]
