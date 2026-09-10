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

# scripts/ is not swept wholesale here: most of its ~25 bare `except Exception`
# sites are single-shot CLI scripts, not worker-pool bulkheads, and each needs
# its own narrow-vs-cite judgment call. These are the ones confirmed (by direct
# read) to be genuine per-item bulkheads structurally identical to the four
# sites ADR 0011 already blesses -- each wraps one independent unit of work
# (an LLM call, an IA upload) inside a loop over many dates/batches/documents
# and already calls `logger.exception(...)` before returning a failure
# sentinel to the caller's loop, satisfying the ADR's substantive test.
_SCRIPTS_CHECKED = {
    REPO_ROOT / "scripts" / "annotate_with_llm.py",
    REPO_ROOT / "scripts" / "pipeline" / "embed_v2.py",
}

# These scripts/ sites were read end-to-end and are single-shot CLI
# operations (parsing a local CSV, downloading one fallback manifest URL) --
# not per-item work inside a worker-pool loop -- so ADR 0011's bulkhead
# carve-out does not apply. They must be narrowed to specific exception
# types instead of citing the ADR.
_SCRIPTS_NARROWED = {REPO_ROOT / "scripts" / "append_manifest.py"}


def _except_exception_lines_in(paths: set[Path]) -> list[tuple[Path, int, str]]:
    hits = []
    for path in paths:
        if path in _GRANDFATHERED:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _EXCEPT_EXCEPTION_RE.match(line):
                hits.append((path, lineno, line))
    return hits


def _except_exception_lines() -> list[tuple[Path, int, str]]:
    return _except_exception_lines_in(set(SRC_ROOT.rglob("*.py")))


def _offenders(hits: list[tuple[Path, int, str]]) -> list[str]:
    return [
        f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}"
        for path, lineno, line in hits
        if ADR_REFERENCE not in line
    ]


def test_every_except_exception_in_src_cites_the_bulkhead_adr():
    offenders = _offenders(_except_exception_lines())
    assert not offenders, (
        "Found `except Exception` without a docs/adr/0011 citation -- either narrow "
        "to specific exception types, or if this is a genuine per-item bulkhead, add "
        "a comment citing docs/adr/0011 (see CLAUDE.md's 'No blind except Exception' "
        "rule):\n" + "\n".join(offenders)
    )


def test_confirmed_scripts_bulkheads_cite_the_bulkhead_adr():
    offenders = _offenders(_except_exception_lines_in(_SCRIPTS_CHECKED))
    assert not offenders, (
        "These scripts/ per-item bulkheads (annotate_with_llm.py's per-batch/"
        "per-document LLM calls, embed_v2.py's per-date/tribunal IA upload) "
        "already satisfy docs/adr/0011's substantive test (per-item work inside "
        "a loop, full traceback logged via logger.exception) but are missing "
        "the required citation:\n" + "\n".join(offenders)
    )


def test_append_manifest_narrows_except_exception_to_specific_types():
    hits = _except_exception_lines_in(_SCRIPTS_NARROWED)
    assert not hits, (
        "scripts/append_manifest.py's except-Exception sites are single-shot CLI "
        "operations, not per-item worker-pool bulkheads -- narrow them to the "
        "specific exception types they can actually raise instead of citing "
        "docs/adr/0011:\n"
        + "\n".join(
            f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}" for path, lineno, line in hits
        )
    )
