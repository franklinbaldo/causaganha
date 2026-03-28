from pathlib import Path
p = Path("src/causaganha/pipeline/orchestration.py")
c = p.read_text()
# Swap the imports
lines = c.splitlines()
f = [l for l in lines if "from __future__" in l]
o = [l for l in lines if "from __future__" not in l]

if f:
    if o[0].startswith('"""'):
        o.insert(1, f[0])
    else:
        o.insert(0, f[0])
    p.write_text("\n".join(o) + "\n")
