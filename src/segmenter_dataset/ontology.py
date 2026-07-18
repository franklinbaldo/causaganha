"""Ontology versioning and migration-impact classification.

RFC 0012 §5.1: ontology v8 = v7 frozen, versioned by semver
(``segmenter-ontology-v8.0.0``). Future changes follow an explicit migration
analysis instead of a blanket "any change invalidates everything":

- adding a category is a **minor** bump — existing annotations stay valid,
  but (§5.1, §8) they must NOT be read as negative examples for the new
  category. An annotation only supervises a category if that category is in
  its own ``covered_categories`` (see ``schemas.AnnotationRecord``);
- removing a category is **major** — invalidates only that category's
  labels in existing records, not the whole record;
- renaming without a semantic change is **minor** — mechanical remap;
- redefining a category's semantics is **major** — treated as remove+add;
- a guideline-only change bumps ``guideline_version`` independently of
  ``ontology_version`` and does not invalidate annotations by default.

This module does not implement the remap/re-annotation workflows themselves
(that is dataset-maintainer process, §5.1) — it only defines the version
identity and the impact classification a maintainer must record.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


_SEMVER_RE = re.compile(r"^segmenter-ontology-v(\d+)\.(\d+)\.(\d+)$")

# RFC 0012 §5.1: v8 = v7 frozen. ref_normativa stays out of the trainable
# space (RFC 0001 — regex pre-pass at inference), matching the current
# data/segmenter_splits/label_space.json on main (25 trainable categories).
ONTOLOGY_V8 = "segmenter-ontology-v8.0.0"

# RFC 0012 §5 point 7: a single-anchor category's "at most one per document"
# default (mechanical.validate_single_anchor_duplicates) fits categories whose
# value is a fact about the *decision as a whole* — dispositivo_abertura and
# resultado are singular by design (guideline Rule 2: only the operative
# mention counts, not every occurrence in reasoning prose), and ref_processual
# is singular because its job is record-linking this text to one case (a
# multi-valued link is useless). It does NOT fit a citation/reasoning
# category, where a real document legitimately repeats itself: fundamentacao_legal
# anchors a distinct statute citation each time it appears, and
# valor_condenacao can name more than one genuinely different amount (moral +
# material damages, or an original vs. a corrected figure) in one decision.
# Deduping those down to "first occurrence" silently drops real signal — see
# the batch1 finding in RFC 0012 §9's pilot history. Every mechanical.validate_record
# call across the pipeline (release gate, both ingestion scripts) must pass
# this set, not decide independently, or the policy drifts.
ALLOW_MULTIPLE_SINGLE_ANCHOR = frozenset({"fundamentacao_legal", "valor_condenacao"})


class MigrationImpact(StrEnum):
    """Semver bump class for an ontology change (RFC 0012 §5.1)."""

    MINOR = "minor"
    MAJOR = "major"


class MigrationKind(StrEnum):
    """The five change kinds RFC 0012 §5.1 distinguishes."""

    ADD_CATEGORY = "add_category"
    REMOVE_CATEGORY = "remove_category"
    RENAME_CATEGORY = "rename_category"
    REDEFINE_CATEGORY = "redefine_category"
    GUIDELINE_ONLY = "guideline_only"


_IMPACT_BY_KIND: dict[MigrationKind, MigrationImpact] = {
    MigrationKind.ADD_CATEGORY: MigrationImpact.MINOR,
    MigrationKind.REMOVE_CATEGORY: MigrationImpact.MAJOR,
    MigrationKind.RENAME_CATEGORY: MigrationImpact.MINOR,
    MigrationKind.REDEFINE_CATEGORY: MigrationImpact.MAJOR,
    MigrationKind.GUIDELINE_ONLY: MigrationImpact.MINOR,
}


@dataclass(frozen=True)
class OntologyVersion:
    """A parsed ``segmenter-ontology-vMAJOR.MINOR.PATCH`` identifier."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Render as ``segmenter-ontology-vMAJOR.MINOR.PATCH``."""
        return f"segmenter-ontology-v{self.major}.{self.minor}.{self.patch}"

    def bump(self, impact: MigrationImpact) -> OntologyVersion:
        """Next version after a change of the given impact class."""
        if impact is MigrationImpact.MAJOR:
            return OntologyVersion(self.major + 1, 0, 0)
        return OntologyVersion(self.major, self.minor + 1, 0)


def parse_ontology_version(value: str) -> OntologyVersion:
    """Parse ``segmenter-ontology-vMAJOR.MINOR.PATCH``; raises ValueError otherwise."""
    match = _SEMVER_RE.match(value)
    if match is None:
        msg = f"not a valid ontology version string: {value!r}"
        raise ValueError(msg)
    major, minor, patch = (int(part) for part in match.groups())
    return OntologyVersion(major, minor, patch)


def classify_migration(kind: MigrationKind) -> MigrationImpact:
    """Map a migration kind to its semver impact class (RFC 0012 §5.1)."""
    return _IMPACT_BY_KIND[kind]


def requires_rfc_amendment(impact: MigrationImpact) -> bool:
    """RFC 0012 §5.1: major changes need this RFC (or a successor) amended.

    Minor changes may be decided by the dataset maintainer and recorded in
    the release manifest instead.
    """
    return impact is MigrationImpact.MAJOR


def load_categories(label_space_path: Path) -> set[str]:
    """Load the trainable category set from a ``label_space.json`` file.

    Excludes the reserved ``"O"`` (outside-any-span) pseudo-category —
    mirrors ``validators.load_label_space_categories`` from PR #832.
    """
    data = json.loads(label_space_path.read_text(encoding="utf-8"))
    names = data.get("span_class_names") or []
    return {name for name in names if name != "O"}
