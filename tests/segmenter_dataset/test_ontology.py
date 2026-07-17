from __future__ import annotations

import json
from pathlib import Path

import pytest

from segmenter_dataset.ontology import (
    MigrationImpact,
    MigrationKind,
    OntologyVersion,
    classify_migration,
    load_categories,
    parse_ontology_version,
    requires_rfc_amendment,
)


def test_parse_ontology_version_round_trip() -> None:
    version = parse_ontology_version("segmenter-ontology-v8.0.0")
    assert version == OntologyVersion(8, 0, 0)
    assert str(version) == "segmenter-ontology-v8.0.0"


def test_parse_ontology_version_rejects_bad_string() -> None:
    with pytest.raises(ValueError, match="not a valid ontology version"):
        parse_ontology_version("v8")


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (MigrationKind.ADD_CATEGORY, MigrationImpact.MINOR),
        (MigrationKind.REMOVE_CATEGORY, MigrationImpact.MAJOR),
        (MigrationKind.RENAME_CATEGORY, MigrationImpact.MINOR),
        (MigrationKind.REDEFINE_CATEGORY, MigrationImpact.MAJOR),
        (MigrationKind.GUIDELINE_ONLY, MigrationImpact.MINOR),
    ],
)
def test_classify_migration(kind: MigrationKind, expected: MigrationImpact) -> None:
    assert classify_migration(kind) == expected


def test_bump_minor_keeps_major() -> None:
    version = OntologyVersion(8, 0, 0)
    assert version.bump(MigrationImpact.MINOR) == OntologyVersion(8, 1, 0)


def test_bump_major_resets_minor_patch() -> None:
    version = OntologyVersion(8, 3, 0)
    assert version.bump(MigrationImpact.MAJOR) == OntologyVersion(9, 0, 0)


def test_requires_rfc_amendment_only_for_major() -> None:
    assert requires_rfc_amendment(MigrationImpact.MAJOR) is True
    assert requires_rfc_amendment(MigrationImpact.MINOR) is False


def test_load_categories_excludes_o(tmp_path: Path) -> None:
    label_space = tmp_path / "label_space.json"
    label_space.write_text(json.dumps({"span_class_names": ["O", "a", "b"]}), encoding="utf-8")
    assert load_categories(label_space) == {"a", "b"}


def test_load_categories_matches_real_label_space() -> None:
    real_path = Path("data/segmenter_splits/label_space.json")
    if not real_path.exists():
        pytest.skip("data/segmenter_splits/label_space.json not present in this checkout")
    categories = load_categories(real_path)
    assert "ref_normativa" not in categories
    assert "dispositivo_abertura" in categories
