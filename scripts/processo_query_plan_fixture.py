#!/usr/bin/env python3
"""Materialize the shared processo query-plan fixtures for the #1107 parity harness.

Writes `<output_dir>/manifest.json` describing every fixture parquet path,
grouped by fonte, plus the CNJs the fixtures are built around. Consumed by
`scripts/processo_query_plan_compare.py` and by the Web/Vitest parity test
(`web/src/lib/processoQueryPlanParity.test.ts`), so both runtimes execute
their query plans against the exact same rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from causaganha.processos.query_plan_fixtures import (  # noqa: E402 — sys.path bootstrap above
    CNJ_ALL,
    CNJ_DJEN_ONLY,
    CNJ_SOURCE_UNAVAILABLE,
    CNJ_TIEBREAK,
    CNJ_UNKNOWN,
    build_fixtures,
)


def write_manifest(output_dir: Path) -> dict:
    fixtures = build_fixtures(output_dir)
    manifest = {
        "cnj_all": CNJ_ALL,
        "cnj_djen_only": CNJ_DJEN_ONLY,
        "cnj_unknown": CNJ_UNKNOWN,
        "cnj_tiebreak": CNJ_TIEBREAK,
        "cnj_source_unavailable": CNJ_SOURCE_UNAVAILABLE,
        "indice_url": str(fixtures["indice"]),
        "report_url": str(fixtures["report"]),
        "missing_djen_url": str(fixtures["missing_djen"]),
        "urls": {
            "djen": [str(fixtures["comunicacoes"])],
            "juris": [str(fixtures["juris"])],
            "stj": [str(fixtures["stj"])],
            "datajud": [str(fixtures["datajud"])],
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(args.output_dir)


if __name__ == "__main__":
    main()
