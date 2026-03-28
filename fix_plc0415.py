import json
from pathlib import Path
from collections import defaultdict

errors = json.load(open('ruff_plc0415.json'))
files = defaultdict(list)
for e in errors:
    files[e['filename']].append(e)

for filename, errs in files.items():
    p = Path(filename)
    if not p.exists(): continue
    lines = p.read_text().splitlines()

    extracted_imports = []

    # Sort backwards
    errs.sort(key=lambda x: x['location']['row'], reverse=True)

    for err in errs:
        row = err['location']['row'] - 1
        line = lines[row]
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            extracted_imports.append(stripped)
            lines.pop(row)

    if extracted_imports:
        # Find the end of `from __future__` or start of imports
        insert_idx = 0
        in_docstring = False
        for i, l in enumerate(lines):
            if l.startswith('"""'):
                if in_docstring:
                    in_docstring = False
                    insert_idx = i + 1
                else:
                    in_docstring = True
                continue

            if not in_docstring:
                if l.startswith("from __future__ import"):
                    insert_idx = i + 1
                    continue
                if l.startswith("import ") or l.startswith("from "):
                    insert_idx = i
                    break

        extracted_imports.reverse()
        for imp in reversed(extracted_imports):
            if imp not in lines:
                lines.insert(insert_idx, imp)

    p.write_text("\n".join(lines) + "\n")
