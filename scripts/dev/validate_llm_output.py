#!/usr/bin/env python3
"""Validate LLM extraction JSON using Pydantic models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.models.llm_output import ExtractionResult
from src.utils.logging_config import setup_logging, get_logger


def validate_file(path: Path) -> bool:
    logger = get_logger(__name__)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ExtractionResult.model_validate(data)
        logger.info("%s validated successfully", path)
        return True
    except Exception as exc:  # broad catch to report any validation error
        logger.error("Validation failed for %s: %s", path, exc)
        return False


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
