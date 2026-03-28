from pathlib import Path
import re

p = Path("src/causaganha/pipeline/ia_download.py")
if p.exists():
    c = p.read_text()
    c = c.replace("cache_path.stat(, tz=timezone.utc).st_mtime", "cache_path.stat().st_mtime, tz=timezone.utc")
    c = c.replace("file_path.stat(, tz=timezone.utc).st_mtime", "file_path.stat().st_mtime, tz=timezone.utc")
    p.write_text(c)

p = Path("scripts/generate_dashboard_cache.py")
if p.exists():
    c = p.read_text()
    c = c.replace("date_type.today()", "datetime.now(timezone.utc).date()")
    p.write_text(c)
