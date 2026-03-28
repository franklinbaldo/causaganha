#!/usr/bin/env python3
"""Parses MkDocs build logs and generates a compact warnings digest."""

import sys
import json
import re
import os
from collections import defaultdict

def parse_logs(log_content):
    warnings = defaultdict(list)
    missing_nav = []

    lines = log_content.splitlines()
    in_missing_nav_block = False

    for line in lines:
        if "The following pages exist in the docs directory, but are not included in the \"nav\" configuration:" in line:
            in_missing_nav_block = True
            continue

        if in_missing_nav_block:
            if line.strip().startswith("- "):
                missing_nav.append(line.strip()[2:])
                continue
            elif "WARNING - " in line or "INFO - " in line:
                in_missing_nav_block = False
            else:
                continue

        if "WARNING - " in line:
            warning_msg = line.split("WARNING - ", 1)[1].strip()

            if "included in the 'nav' configuration, which is not found" in warning_msg:
                match = re.search(r"A reference to '([^']+)' is included", warning_msg)
                if match:
                    warnings['missing_nav_targets'].append(match.group(1))
            elif "contains a link" in warning_msg and "is not found among documentation files" in warning_msg:
                match = re.search(r"Doc file '([^']+)' contains a link '([^']+)', but the target '([^']+)' is not found", warning_msg)
                if match:
                    warnings['broken_links'].append({
                        'file': match.group(1),
                        'link': match.group(2),
                        'target': match.group(3)
                    })
            elif "mkdocs_autorefs" in warning_msg and "Could not find cross-reference target" in warning_msg:
                match = re.search(r"mkdocs_autorefs: ([^:]+): Could not find cross-reference target '([^']+)'", warning_msg)
                if match:
                    warnings['broken_autorefs'].append({
                        'file': match.group(1),
                        'target': match.group(2)
                    })
            elif "git-revision-date-localized-plugin" in warning_msg or "fetch-depth" in warning_msg:
                warnings['git_revision'].append(warning_msg)
            else:
                warnings['other'].append(warning_msg)

    return warnings, missing_nav

def generate_digest(warnings, missing_nav, output_path):
    digest = {
        'summary': {
            'total_warnings': sum(len(v) for v in warnings.values()) + len(missing_nav),
            'categories': {
                'missing_nav_targets': len(warnings.get('missing_nav_targets', [])),
                'broken_links': len(warnings.get('broken_links', [])),
                'broken_autorefs': len(warnings.get('broken_autorefs', [])),
                'orphaned_docs': len(missing_nav),
                'git_revision_warnings': len(warnings.get('git_revision', [])),
                'other': len(warnings.get('other', []))
            }
        },
        'details': {
            'missing_nav_targets': warnings.get('missing_nav_targets', []),
            'broken_links_examples': warnings.get('broken_links', [])[:5],
            'broken_autorefs': warnings.get('broken_autorefs', []),
            'orphaned_docs_examples': missing_nav[:5],
            'git_revision_warnings': warnings.get('git_revision', []),
            'other_examples': warnings.get('other', [])[:5]
        }
    }

    with open(output_path, 'w') as f:
        json.dump(digest, f, indent=2)

    print(f"Docs warning digest generated at {output_path}")
    print(json.dumps(digest['summary'], indent=2))

    # Generate markdown summary for GitHub Step Summary
    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a') as f:
            f.write("# 📚 Docs Warnings Digest\n\n")
            f.write(f"**Total Warnings:** {digest['summary']['total_warnings']}\n\n")

            f.write("### 📊 Summary by Category\n")
            for cat, count in digest['summary']['categories'].items():
                if count > 0:
                    f.write(f"- **{cat.replace('_', ' ').title()}:** {count}\n")

            if digest['details']['missing_nav_targets']:
                f.write("\n### ❌ Missing Nav Targets\n")
                for item in digest['details']['missing_nav_targets']:
                    f.write(f"- `{item}`\n")

            if digest['details']['broken_links_examples']:
                f.write("\n### 🔗 Broken Links (Top 5)\n")
                for item in digest['details']['broken_links_examples']:
                    f.write(f"- In `{item['file']}`: Link to `{item['link']}` (target not found)\n")

            if digest['details']['orphaned_docs_examples']:
                f.write("\n### 👻 Orphaned Docs (Not in Nav - Top 5)\n")
                for item in digest['details']['orphaned_docs_examples']:
                    f.write(f"- `{item}`\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: parse_mkdocs_logs.py <log_file> <output_json>")
        sys.exit(1)

    log_file = sys.argv[1]
    output_json = sys.argv[2]

    try:
        with open(log_file, 'r') as f:
            log_content = f.read()

        warnings, missing_nav = parse_logs(log_content)
        generate_digest(warnings, missing_nav, output_json)
    except Exception as e:
        print(f"Error parsing logs: {e}")
        sys.exit(1)
