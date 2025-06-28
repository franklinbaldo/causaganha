#!/usr/bin/env python3
"""Bootstrap new tribunal adapter skeleton."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEMPLATES = {
    "__init__.py": "",
    "adapter.py": "class {name}Adapter:\n    tribunal_code = '{code}'\n",
    "discovery.py": "class {name}Discovery:\n    pass\n",
    "downloader.py": "class {name}Downloader:\n    pass\n",
    "analyze_adapter.py": "class {name}Analyzer:\n    pass\n",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create tribunal adapter skeleton")
    parser.add_argument("code", help="Tribunal code, e.g. tjsp")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "src" / "tribunais" / args.code
    if target.exists():
        print(f"Directory {target} already exists", file=sys.stderr)
        raise SystemExit(1)

    target.mkdir(parents=True)
    class_name = args.code.upper()
    for fname, template in TEMPLATES.items():
        (target / fname).write_text(template.format(name=class_name, code=args.code))

    print(f"Created tribunal adapter skeleton in {target}")


if __name__ == "__main__":
    main()
