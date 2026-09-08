"""README.md's optional-contracts list must match the .qmd frontmatter it describes."""

from __future__ import annotations

import re
from pathlib import Path

from scripts import render_queries as rq


REPO_ROOT = Path(__file__).resolve().parents[1]
README = rq.QUERIES_DIR / "README.md"

_OPTIONAL_LIST_RE = re.compile(r"Currently optional:\s*(.+?)\.", re.DOTALL)


def _readme_optional_names() -> set[str]:
    text = README.read_text(encoding="utf-8")
    match = _OPTIONAL_LIST_RE.search(text)
    assert match, "README.md must document a 'Currently optional: ...' contract list"
    normalized = re.sub(r"\s+", " ", match.group(1))
    return {name.strip(" `") for name in normalized.split(",")}


def _actual_optional_names() -> set[str]:
    names = set()
    for path in rq.QUERIES_DIR.glob("*.qmd"):
        frontmatter, _sql = rq.parse_qmd(path)
        if frontmatter.get("optional") is True:
            names.add(path.stem)
    return names


def test_readme_optional_contracts_list_matches_qmd_frontmatter():
    documented = _readme_optional_names()
    actual = _actual_optional_names()
    assert documented == actual, (
        f"README.md's 'Currently optional' list is stale: "
        f"missing {actual - documented}, stale entries {documented - actual}"
    )
