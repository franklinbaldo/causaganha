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

A third defect was introduced when the hourly loop switched from the git-hosted
`wikiskill` package to the published `wisk` PyPI package (#1251, #1260):
`wisk.bootstrap.init_repository` hardcodes its managed-bundle target to
`<repo>/.wisk`, not `<repo>/.wikiskill`. `.claude/hourly-loop.md` still documents
plain `wisk init .` / `wisk session start-next ...` with no `--path`, and
`wisk`'s own CLI defaults an unqualified command to `.wisk/knowledge` whenever
that directory exists. The net effect: every hourly-loop round silently
bootstraps and records its LoopRun/Experience state under the gitignored
`.wisk/` tree instead of the tracked `.wikiskill/knowledge/` one, so all of
that round's readings/goals/evidence/checks/outcomes vanish the moment the
container is torn down. Making `.wisk` a symlink to `.wikiskill` closes this:
`wisk init .` then writes its generated `manifest.json`, `specs/`, and
`knowledge/system/` straight into `.wikiskill/` (ignored there by the nested
`.gitignore` `wisk init .` itself writes), and an unqualified
`wisk session start-next ...` resolves its default path to `.wisk/knowledge`,
which -- through the symlink -- *is* `.wikiskill/knowledge`, so records land in
the tracked namespaces without needing an explicit `--path` on every call.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from okf_parser.service import check_bundle

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKISKILL_ROOT = REPO_ROOT / ".wikiskill"
WIKISKILL_KNOWLEDGE = WIKISKILL_ROOT / "knowledge"
WISK_ROOT = REPO_ROOT / ".wisk"

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


def test_wisk_root_is_a_symlink_into_wikiskill() -> None:
    assert WISK_ROOT.is_symlink(), (
        "'.wisk' must be a tracked symlink into '.wikiskill' so that "
        "'wisk init .' bootstraps its managed bundle (manifest.json, specs/, "
        "knowledge/system/) directly under the git-tracked knowledge tree, and "
        "an unqualified 'wisk session start-next ...' -- as documented in "
        "'.claude/hourly-loop.md' -- records its LoopRun/Experience state under "
        "'.wikiskill/knowledge/' instead of silently writing it into a separate, "
        "gitignored '.wisk/' tree that is lost when the container is torn down."
    )
    assert WISK_ROOT.resolve() == WIKISKILL_ROOT
