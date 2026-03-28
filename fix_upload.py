from pathlib import Path

p = Path("scripts/upload_to_ia.py")
content = p.read_text()
content = content.replace("    try:\n        # Try to import internetarchive\n    except ImportError:", "    try:\n        pass\n    except ImportError:")
p.write_text(content)
