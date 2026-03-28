import re
from pathlib import Path

dtz_rules = ["DTZ003", "DTZ005", "DTZ007", "DTZ011", "DTZ006"]

def fix_file(filepath):
    p = Path(filepath)
    if not p.exists(): return
    c = p.read_text()
    orig = c

    # Add timezone import if needed
    if "timezone" not in c and any(sub in c for sub in ["datetime.now(", "datetime.utcnow(", "date.today()"]):
        # Insert after "from datetime import datetime" or similar
        c = re.sub(r'(from datetime import .*?datetime.*?)', r'\1, timezone', c)
        if "from datetime import timezone" not in c:
            c = "from datetime import timezone\n" + c

    # Replace specific bad patterns
    # DTZ003/DTZ005: datetime.now() -> datetime.now(timezone.utc)
    #                datetime.utcnow() -> datetime.now(timezone.utc)
    c = re.sub(r'\bdatetime\.now\(\)', 'datetime.now(timezone.utc)', c)
    c = re.sub(r'\bdatetime\.utcnow\(\)', 'datetime.now(timezone.utc)', c)

    # DTZ011: date.today() -> datetime.now(timezone.utc).date()
    c = re.sub(r'\bdate\.today\(\)', 'datetime.now(timezone.utc).date()', c)

    # DTZ007: datetime.strptime(..., "...") -> datetime.strptime(..., "...").replace(tzinfo=timezone.utc)
    c = re.sub(r'datetime\.strptime\(([^)]+)\)', r'datetime.strptime(\1).replace(tzinfo=timezone.utc)', c)

    # DTZ006: datetime.fromtimestamp(...) -> datetime.fromtimestamp(..., tz=timezone.utc)
    c = re.sub(r'datetime\.fromtimestamp\(([^),]+)\)', r'datetime.fromtimestamp(\1, tz=timezone.utc)', c)

    if orig != c:
        p.write_text(c)

for f in set([line.split(":")[0].strip() for line in open("ruff_dtz.json").read().splitlines() if line.strip()]):
    pass

import json
errors = json.load(open('ruff_dtz.json'))
for f in set(e['filename'] for e in errors):
    if f.endswith(".py") or f.endswith(".ipynb"):
        fix_file(f)
