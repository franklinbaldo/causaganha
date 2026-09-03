"""Emit schema/join-candidate evidence for acquired TSE Processual ZIPs."""

from __future__ import annotations

import argparse
from pathlib import Path

from tse_processual.inspection import write_inspection_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "archives",
        nargs="+",
        type=Path,
        help="Official Processo/Assuntos/Decisões ZIP files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination JSON evidence report",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=1000,
        help="Rows sampled per CSV for generation metadata",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    write_inspection_report(args.archives, args.output, sample_rows=args.sample_rows)
    print(args.output)


if __name__ == "__main__":
    main()
