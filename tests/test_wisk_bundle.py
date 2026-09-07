"""Regression guards for the canonical Wisk consumer bundle."""

from __future__ import annotations

import subprocess
from pathlib import Path

from okf_parser.service import check_bundle

REPO_ROOT = Path(__file__).resolve().parent.parent
WISK_ROOT = REPO_ROOT / ".wisk"
WISK_KNOWLEDGE = WISK_ROOT / "knowledge"
LEGACY_ROOT = REPO_ROOT / ".wikiskill"

_PRESERVED_NAMESPACES = ("local", "experiences", "wiki", "skills")


def test_wisk_knowledge_bundle_is_okf_conformant() -> None:
    report = check_bundle(str(WISK_KNOWLEDGE))
    assert report["conformant"] is True, report["diagnostics"]


def test_no_unmanaged_files_outside_preserved_wisk_namespaces() -> None:
    preserved_prefixes = tuple(f"knowledge/{name}/" for name in _PRESERVED_NAMESPACES)
    tracked = subprocess.run(
        ["git", "ls-files", "--", ".wisk"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    stray = [
        path
        for path in tracked
        if not path.removeprefix(".wisk/").startswith(preserved_prefixes)
    ]
    assert stray == []


def test_wisk_is_canonical_and_legacy_root_is_gone() -> None:
    assert WISK_ROOT.is_dir()
    assert not WISK_ROOT.is_symlink()
    assert not LEGACY_ROOT.exists(), (
        "'.wikiskill' must not reappear as a parallel runtime namespace; "
        "all historical and new Wisk state belongs under '.wisk'."
    )
