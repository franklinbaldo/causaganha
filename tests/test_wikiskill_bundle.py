"""`.wikiskill/knowledge/` must stay a bootstrappable WikiSkill consumer bundle.

`wikiskill init .` (see `.claude/hourly-loop.md`) refuses to finish bootstrapping
in two independent ways if this tree regresses:

1. `wikiskill.bootstrap.init_repository` treats any file directly under
   `.wikiskill/` that isn't nested inside one of its preserved namespaces
   (`knowledge/{local,experiences,wiki,skills}`) as unmanaged state and aborts
   with `status: unmanaged-existing-state` before ever writing `manifest.json`.
2. Even inside those namespaces, `wikiskill` validates every Markdown file as
   an OKF concept requiring YAML frontmatter unless it uses a filename okf-parser
   reserves (`index.md`, `log.md` -- see `okf_parser.parser.RESERVED_FILENAMES`).
   A plain `README.md` fails that check and `init_repository` reports
   `status: initialized` as `"conformant": false`, then rolls back.

Commit 4c8828b ("migrate hourly loop to WikiSkill") introduced exactly these
two defects, leaving the hourly loop's `wikiskill session start-next` call
permanently failing with "No SessionType is currently eligible for requested
start." This test guards the underlying bundle shape directly with the
project's own pinned `okf-parser` dependency, without needing network access
to fetch the `wikiskill`/`wisk` package itself.

The second check walks *tracked* files (`git ls-files`), not the raw
filesystem: running `wikiskill init .` locally legitimately drops generated,
gitignored state (`manifest.json`, `specs/`, `knowledge/system/`) straight
under `.wikiskill/`, which is fine at runtime but must never be committed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from okf_parser.service import check_bundle

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKISKILL_ROOT = REPO_ROOT / ".wikiskill"
WIKISKILL_KNOWLEDGE = WIKISKILL_ROOT / "knowledge"

_PRESERVED_NAMESPACES = ("local", "experiences", "wiki", "skills")


def test_wikiskill_knowledge_bundle_is_okf_conformant() -> None:
    report = check_bundle(str(WIKISKILL_KNOWLEDGE))

    assert report["conformant"] is True, report["diagnostics"]


def test_no_unmanaged_files_outside_preserved_wikiskill_namespaces() -> None:
    preserved_prefixes = tuple(f"knowledge/{name}/" for name in _PRESERVED_NAMESPACES)

    tracked = subprocess.run(
        ["git", "ls-files", "--", ".wikiskill"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    stray = [
        path
        for path in tracked
        if not path.removeprefix(".wikiskill/").startswith(preserved_prefixes)
    ]

    assert stray == []
