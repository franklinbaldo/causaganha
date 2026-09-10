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
    # scripts/pipeline/consolidate.py: read end-to-end. 6 of its 10 sites are
    # genuine per-item bulkheads (per-date marker upload, per-table export,
    # per-zip ndjson write, two per-zip as_completed loops, the backfill
    # while-loop over dates) structurally identical to the ones ADR 0011
    # already blesses -- including src/causaganha/consolidate/cli.py:172's
    # own per-table bulkhead, the ADR's own cited example. The other 4 sites
    # (checkpoint save, and the three single-shot main() CLI branches that
    # each run exactly once per invocation, not in a loop) were narrowed to
    # specific exception types instead.
    REPO_ROOT / "scripts" / "pipeline" / "consolidate.py",
    # scripts/dev/cleanup_deprecated_ia_items.py: read end-to-end. Its 2
    # remaining bulkhead sites (get_item_metadata, delete_ia_file) are each
    # called from two different loops over independent IA items/files
    # (the outer `for item in items` search-results loop, and per-file
    # deletion/verification loops nested inside it) -- structurally the
    # same per-item-inside-a-loop-over-many shape ADR 0011 blesses, even
    # though each wraps a narrow single-HTTP-call surface. The third site
    # (the initial IA search request) runs once per script invocation, not
    # in a loop, so it was narrowed instead (see _SCRIPTS_NARROWED).
    REPO_ROOT / "scripts" / "dev" / "cleanup_deprecated_ia_items.py",
    # build_gold_benchmark.py and daily_benchmark_update.py: each wraps one
    # LLMAnalyzer call inside a loop over many independent batches/documents
    # (`for batch in track(batches, ...)`, `for ... in track(selected_for_labeling,
    # ...)`) and continues to the next iteration on failure rather than
    # aborting -- the same shape as the four sites ADR 0011 already blesses.
    # Neither file uses structlog, so ruff's own `.exception(...)` BLE001
    # exemption doesn't apply here; each keeps its `noqa: BLE001` alongside
    # the ADR citation, and now also calls `console.print_exception()` to
    # actually satisfy the ADR's full-traceback-logging condition instead of
    # only printing the exception's string form.
    REPO_ROOT / "scripts" / "build_gold_benchmark.py",
    REPO_ROOT / "scripts" / "daily_benchmark_update.py",
}

# These scripts/ sites were read end-to-end and are single-shot CLI
# operations (parsing a local CSV, downloading one fallback manifest URL,
# one DuckDB connect/build call each, one best-effort metrics write) --
# not per-item work inside a worker-pool loop -- so ADR 0011's bulkhead
# carve-out does not apply. They must be narrowed to specific exception
# types instead of citing the ADR.
_SCRIPTS_NARROWED = {
    REPO_ROOT / "scripts" / "append_manifest.py",
    REPO_ROOT / "scripts" / "generate_catalog.py",
    # batch_embed_decisions.py's 3 sites (file upload, batch-job creation, one
    # job's status poll) are each single-shot or poll-the-same-single-resource
    # operations, not per-item work inside a loop over many independent units
    # -- despite the file's own prior noqa comment implying otherwise, no site
    # here is actually a bulkhead. Narrowed to google.genai.errors.APIError,
    # importable unconditionally since the module already does
    # `from google import genai` at load time (the "lab" dependency group).
    REPO_ROOT / "scripts" / "batch_embed_decisions.py",
}


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
        "These scripts/ sites already satisfy docs/adr/0011's substantive test "
        "(per-item work inside a loop over many independent units, with the "
        "full exception surfaced for postmortem via logger.exception or, where "
        "no logger exists, console.print_exception) but are missing the "
        "required citation:\n" + "\n".join(offenders)
    )


def test_narrowed_scripts_have_no_bare_except_exception():
    hits = _except_exception_lines_in(_SCRIPTS_NARROWED)
    assert not hits, (
        "These scripts/ except-Exception sites are single-shot CLI operations, "
        "not per-item worker-pool bulkheads -- narrow them to the specific "
        "exception types they can actually raise instead of citing docs/adr/0011:\n"
        + "\n".join(
            f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}" for path, lineno, line in hits
        )
    )
