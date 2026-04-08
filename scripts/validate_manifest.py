#!/usr/bin/env python3
"""Validate the newly generated manifest.jsonl before uploading."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def fetch_remote_line_count(url: str) -> int:
    """Fetch remote manifest and return line count."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                content = response.read().decode("utf-8").strip()
                if not content:
                    return 0
                return len([line for line in content.splitlines() if line.strip()])
    except urllib.error.URLError as e:
        print(f"Warning: Failed to fetch remote manifest at {url}: {e}")
        return 0
    except Exception as e:
        print(f"Warning: Unexpected error fetching remote manifest at {url}: {e}")
        return 0
    return 0


def main():
    parser = argparse.ArgumentParser(description="Validate manifest.jsonl")
    parser.add_argument(
        "file_path", nargs="?", default="data/manifest.jsonl", help="Path to manifest.jsonl"
    )
    args = parser.parse_args()

    manifest_path = Path(args.file_path)

    if not manifest_path.exists():
        print(f"Error: Manifest file '{manifest_path}' does not exist.")
        sys.exit(1)

    try:
        content = manifest_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"Error: Failed to read manifest file '{manifest_path}': {e}")
        sys.exit(1)

    if not content:
        print(f"Error: Manifest file '{manifest_path}' is empty.")
        sys.exit(1)

    lines = [line for line in content.splitlines() if line.strip()]
    new_line_count = len(lines)

    if new_line_count == 0:
        print(f"Error: Manifest file '{manifest_path}' has no valid lines.")
        sys.exit(1)

    # Validate JSON lines and required keys
    required_keys = {"date", "tribunal", "zip_url"}
    for i, line in enumerate(lines, 1):
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON on line {i}: {e}")
            sys.exit(1)

        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            print(f"Error: Line {i} is missing required keys: {missing_keys}")
            sys.exit(1)

    # Compare with remote manifest
    remote_url = "https://archive.org/download/causaganha-catalog/manifest.jsonl"
    remote_line_count = fetch_remote_line_count(remote_url)

    if remote_line_count > 0:
        if new_line_count < remote_line_count * 0.95:
            drop_pct = (1 - (new_line_count / remote_line_count)) * 100
            print(
                f"Error: Significant data drop detected! Remote has {remote_line_count} lines, new has {new_line_count} lines ({drop_pct:.2f}% drop)."
            )
            print("To protect the catalog, upload has been aborted.")
            sys.exit(1)
        else:
            print(
                f"Validation passed: New manifest has {new_line_count} lines (Remote has {remote_line_count} lines)."
            )
    else:
        print(
            f"Validation passed: New manifest has {new_line_count} lines (Remote manifest not found or empty)."
        )


if __name__ == "__main__":
    main()
