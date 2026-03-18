#!/usr/bin/env python3
"""Validate LLM extraction JSON using Pydantic models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from causaganha_v1.models.llm_output import ExtractionResult
from causaganha_v1.utils.logging_config import get_logger, setup_logging


def validate_file(path: Path) -> bool:
    logger = get_logger(__name__)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ExtractionResult.model_validate(data)
        logger.info("%s validated successfully", path)
    except Exception:  # broad catch to report any validation error
        logger.exception("Validation failed for %s", path)
        return False
    else:
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate LLM JSON output")
    parser.add_argument("json_files", nargs="+", help="Paths to JSON files")
    args = parser.parse_args()

    setup_logging()

    ok = True
    for file in args.json_files:
        if not validate_file(Path(file)):
            ok = False
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
