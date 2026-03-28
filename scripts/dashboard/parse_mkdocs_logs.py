#!/usr/bin/env python3
"""Parses MkDocs build logs and generates a compact warnings digest."""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def _parse_warning_line(warning_msg: str, warnings: defaultdict) -> None:
    if "included in the 'nav' configuration, which is not found" in warning_msg:
        match = re.search(r"A reference to '([^']+)' is included", warning_msg)
        if match:
            warnings["missing_nav_targets"].append(match.group(1))
    elif "is not found among documentation files" in warning_msg:
        match = re.search(
            r"Doc file '([^']+)' contains a link '([^']+)', "
            r"but the target '([^']+)' is not found",
            warning_msg,
        )
        if match:
            warnings["broken_links"].append({
                "file": match.group(1),
                "link": match.group(2),
                "target": match.group(3)
            })
    elif "mkdocs_autorefs" in warning_msg:
        match = re.search(
            r"mkdocs_autorefs: ([^:]+): Could not find cross-reference target '([^']+)'",
            warning_msg
        )
        if match:
            warnings["broken_autorefs"].append({
                "file": match.group(1),
                "target": match.group(2)
            })
    elif "git-revision-date" in warning_msg or "fetch-depth" in warning_msg:
        warnings["git_revision"].append(warning_msg)
    else:
        warnings["other"].append(warning_msg)

def parse_logs(log_content: str) -> tuple[dict, list]:
    """Parse mkdocs log output to extract and categorize warnings."""
    warnings = defaultdict(list)
    missing_nav = []

    lines = log_content.splitlines()
    in_missing_nav_block = False

    missing_nav_start = (
        'The following pages exist in the docs directory, '
        'but are not included in the "nav" configuration:'
    )

    for line in lines:
        if missing_nav_start in line:
            in_missing_nav_block = True
            continue

        if in_missing_nav_block:
            if line.strip().startswith("- "):
                missing_nav.append(line.strip()[2:])
                continue
            if "WARNING - " in line or "INFO - " in line:
                in_missing_nav_block = False
            else:
                continue

        if "WARNING - " in line:
            warning_msg = line.split("WARNING - ", 1)[1].strip()
            _parse_warning_line(warning_msg, warnings)

    return dict(warnings), missing_nav

def generate_digest(warnings: dict, missing_nav: list, output_path: str) -> None:
    """Generate the json digest and write to GITHUB_STEP_SUMMARY."""
    digest = {
        "summary": {
            "total_warnings": sum(len(v) for v in warnings.values()) + len(missing_nav),
            "categories": {
                "missing_nav_targets": len(warnings.get("missing_nav_targets", [])),
                "broken_links": len(warnings.get("broken_links", [])),
                "broken_autorefs": len(warnings.get("broken_autorefs", [])),
                "orphaned_docs": len(missing_nav),
                "git_revision_warnings": len(warnings.get("git_revision", [])),
                "other": len(warnings.get("other", []))
            }
        },
        "details": {
            "missing_nav_targets": warnings.get("missing_nav_targets", []),
            "broken_links_examples": warnings.get("broken_links", [])[:5],
            "broken_autorefs": warnings.get("broken_autorefs", []),
            "orphaned_docs_examples": missing_nav[:5],
            "git_revision_warnings": warnings.get("git_revision", []),
            "other_examples": warnings.get("other", [])[:5]
        }
    }

    with Path(output_path).open("w") as f:
        json.dump(digest, f, indent=2)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with Path(step_summary).open("a") as f:
            f.write("# 📚 Docs Warnings Digest\n\n")
            f.write(f"**Total Warnings:** {digest['summary']['total_warnings']}\n\n")

            f.write("### 📊 Summary by Category\n")
            for cat, count in digest["summary"]["categories"].items():
                if count > 0:
                    f.write(f"- **{cat.replace('_', ' ').title()}:** {count}\n")

            if digest["details"]["missing_nav_targets"]:
                f.write("\n### ❌ Missing Nav Targets\n")
                f.writelines(f"- `{item}`\n" for item in digest["details"]["missing_nav_targets"])

            if digest["details"]["broken_links_examples"]:
                f.write("\n### 🔗 Broken Links (Top 5)\n")
                f.writelines(
                    f"- In `{item['file']}`: Link to `{item['link']}` (not found)\n"
                    for item in digest["details"]["broken_links_examples"]
                )

            if digest["details"]["orphaned_docs_examples"]:
                f.write("\n### 👻 Orphaned Docs (Not in Nav - Top 5)\n")
                lines = (f"- `{item}`\n" for item in digest["details"]["orphaned_docs_examples"])
                f.writelines(lines)

if __name__ == "__main__":
    REQUIRED_ARGS = 3
    if len(sys.argv) < REQUIRED_ARGS:
        sys.exit(1)

    log_file = sys.argv[1]
    output_json = sys.argv[2]

    try:
        with Path(log_file).open() as f:
            log_content = f.read()

        warnings, missing_nav = parse_logs(log_content)
        generate_digest(warnings, missing_nav, output_json)
    except OSError:
        sys.exit(1)
