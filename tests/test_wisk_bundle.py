"""Regression guards for the canonical Wisk consumer bundle."""

from pathlib import Path

from okf_parser.service import check_bundle

REPO_ROOT = Path(__file__).resolve().parent.parent
WISK_ROOT = REPO_ROOT / ".wisk"
WISK_KNOWLEDGE = WISK_ROOT / "knowledge"
LEGACY_ROOT = REPO_ROOT / ".wikiskill"


def test_wisk_knowledge_bundle_is_okf_conformant() -> None:
    report = check_bundle(str(WISK_KNOWLEDGE))
    assert report["conformant"] is True


def test_wisk_root_is_a_real_directory() -> None:
    assert WISK_ROOT.is_dir()
    assert not WISK_ROOT.is_symlink()


def test_legacy_wikiskill_root_is_gone() -> None:
    assert not LEGACY_ROOT.exists()
