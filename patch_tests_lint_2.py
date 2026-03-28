import re

with open("scripts/dashboard/generate-data.py", "r") as f:
    content2 = f.read()

content2 = content2.replace('date(2026, 2, 3)  # Based on target range end 2026-02-03', 'from datetime import date\n    date(2026, 2, 3)  # Based on target range end 2026-02-03')
content2 = content2.replace('from datetime import date\n    from datetime import date\n    date(2026, 2, 3)', 'from datetime import date\n    date(2026, 2, 3)')

with open("scripts/dashboard/generate-data.py", "w") as f:
    f.write(content2)
