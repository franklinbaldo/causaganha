"""Profile exact key cardinality and joins in TSE Processual 2026 ZIPs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tse_processual.profiling import relational_profile


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processos", type=Path, required=True)
    parser.add_argument("--assuntos", type=Path, required=True)
    parser.add_argument("--decisoes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    report = relational_profile(
        {
            "processos": args.processos,
            "assuntos": args.assuntos,
            "decisoes": args.decisoes,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
