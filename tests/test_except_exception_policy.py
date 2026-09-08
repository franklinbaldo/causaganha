"""Enforce docs/adr/0011: `except Exception` needs a cited justification.

CLAUDE.md bans blind `except Exception` except at a per-item bulkhead inside
a worker-pool loop, and requires that carve-out to cite the ADR. Ruff's
BLE001 already accepts any handler that calls `.exception(...)`, so it can't
catch a new broad catch added without justification -- this test is the
actual enforcement.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
ADR_REFERENCE = "docs/adr/0011"

_EXCEPT_EXCEPTION_RE = re.compile(r"^\s*except\s+Exception\b")

# Files with a BLE001 per-file-ignore in ruff.toml pre-date this policy and
# are grandfathered here rather than retrofitted with ADR comments.
_GRANDFATHERED = {SRC_ROOT / "stj_acordaos" / "__main__.py"}


def _except_exception_lines() -> list[tuple[Path, int, str]]:
    hits = []
    for path in SRC_ROOT.rglob("*.py"):
        if path in _GRANDFATHERED:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _EXCEPT_EXCEPTION_RE.match(line):
                hits.append((path, lineno, line))
    return hits


def test_every_except_exception_in_src_cites_the_bulkhead_adr():
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}"
        for path, lineno, line in _except_exception_lines()
        if ADR_REFERENCE not in line
    ]
    assert not offenders, (
        "Found `except Exception` without a docs/adr/0011 citation -- either narrow "
        "to specific exception types, or if this is a genuine per-item bulkhead, add "
        "a comment citing docs/adr/0011 (see CLAUDE.md's 'No blind except Exception' "
        "rule):\n" + "\n".join(offenders)
    )
