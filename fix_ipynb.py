from pathlib import Path
p = Path("docs/archive/tutorials/tribunal_adapter.ipynb")
c = p.read_text()
c = c.replace("from datetime import timezone\n", "")
c = c.replace("date.today()", "datetime.now(timezone.utc).date()")
p.write_text(c)
