"""CLI entry point for the segmenter dataset lifecycle (RFC 0012).

Two commands, split at the same seam as RFC 0012 §10/§12:

- ``assign-splits`` — groups documents, applies role eligibility, and writes
  a reproducible ``split_manifest.json`` (RFC 0012 §8's intermediate,
  not-yet-a-release artifact — a :class:`~segmenter_dataset.schemas.SplitManifest`,
  not a bare set of IDs).
- ``build-release`` — reads that ``split_manifest.json`` and runs
  ``build_dataset_release`` (RFC 0012 §12), writing the final immutable
  release manifest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import cyclopts.validators
from cyclopts import App, Parameter

from segmenter_dataset.dataset_card import render_dataset_card
from segmenter_dataset.iaa import DEFAULT_BOOTSTRAP_RESAMPLES
from segmenter_dataset.ontology import ONTOLOGY_V8, load_categories
from segmenter_dataset.release import ReleaseBlockedError, build_dataset_release
from segmenter_dataset.schemas import KnownLimitation, SplitManifest
from segmenter_dataset.splits import (
    EmptyEvalSplitError,
    GroupingKeys,
    assign_splits,
    build_groups,
    create_split_manifest,
    evaluation_eligible_document_ids,
    train_eligible_document_ids,
)
from segmenter_dataset.store import SegmenterDatasetStore


if TYPE_CHECKING:
    # Path stays a live import above — the @app.command parameters below need
    # a runtime-resolvable annotation to build the CLI schema. GateResult is
    # only used in a plain helper, not a command, so it's safe to defer.
    from segmenter_dataset.gates import GateResult


app = App(
    help="Segmenter dataset lifecycle (RFC 0012).",
    version_flags=[],
)


@app.command(name="assign-splits")
def assign_splits_command(
    *,
    data_root: Annotated[
        Path,
        Parameter(
            validator=cyclopts.validators.Path(exists=True, file_okay=False), help="data/segmenter/"
        ),
    ],
    output: Annotated[Path, Parameter(help="Where to write split_manifest.json")],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: Annotated[int, Parameter(help="Deterministic assignment seed (RFC 0012 §10)")],
    near_duplicate_threshold: float = 0.9,
) -> int | None:
    """Group documents, apply role eligibility, and write a split manifest."""
    store = SegmenterDatasetStore(data_root)
    documents = store.list_documents()
    annotations = store.list_annotations()
    reviews = store.list_reviews()

    grouping_keys = [GroupingKeys.from_document(doc) for doc in documents]
    groups = build_groups(
        documents, grouping_keys, near_duplicate_threshold=near_duplicate_threshold
    )

    try:
        assignment = assign_splits(
            groups,
            train_eligible=train_eligible_document_ids(annotations),
            evaluation_eligible=evaluation_eligible_document_ids(reviews),
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            seed=seed,
        )
    except EmptyEvalSplitError as exc:
        print(f"assign-splits blocked: {exc}", file=sys.stderr)
        return 1

    manifest = create_split_manifest(
        assignment,
        groups,
        seed=seed,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        near_duplicate_threshold=near_duplicate_threshold,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"wrote {output}: train={len(manifest.train_ids)} "
        f"val={len(manifest.val_ids)} test={len(manifest.test_ids)}"
    )
    return None


@app.command(name="build-release")
def build_release_command(
    *,
    data_root: Annotated[
        Path,
        Parameter(
            validator=cyclopts.validators.Path(exists=True, file_okay=False), help="data/segmenter/"
        ),
    ],
    split_manifest: Annotated[
        Path,
        Parameter(validator=cyclopts.validators.Path(exists=True), help="Output of assign-splits"),
    ],
    release_id: str,
    label_space: Annotated[
        Path,
        Parameter(validator=cyclopts.validators.Path(exists=True), help="Path to label_space.json"),
    ],
    source_commit: Annotated[str, Parameter(help="Full 40-character Git commit SHA")],
    dependency_lock_hash: Annotated[str, Parameter(help="SHA-256 of the pinned lockfile")],
    ci_provider: Annotated[str, Parameter(help="CI provider, e.g. github-actions")],
    ci_run_id: Annotated[str, Parameter(help="Immutable CI run identifier")],
    guideline_version: str,
    iaa_seed: int,
    iaa_resamples: Annotated[
        int, Parameter(validator=cyclopts.validators.Number(gte=1000))
    ] = DEFAULT_BOOTSTRAP_RESAMPLES,
    known_limitations: Annotated[
        Path | None,
        Parameter(
            validator=cyclopts.validators.Path(exists=True), help="JSON list of {gate, reason}"
        ),
    ] = None,
    ontology_version: str = ONTOLOGY_V8,
) -> int | None:
    """Build the immutable dataset release (RFC 0012 §12)."""
    store = SegmenterDatasetStore(data_root)
    manifest = SplitManifest.model_validate_json(split_manifest.read_text(encoding="utf-8"))

    limitations: list[KnownLimitation] = []
    if known_limitations is not None:
        raw = json.loads(known_limitations.read_text(encoding="utf-8"))
        limitations = [KnownLimitation(**entry) for entry in raw]

    ontology_categories = load_categories(label_space)

    try:
        release_manifest = build_dataset_release(
            store,
            release_id=release_id,
            ontology_version=ontology_version,
            guideline_version=guideline_version,
            source_commit=source_commit,
            dependency_lock_hash=dependency_lock_hash,
            ci_provider=ci_provider,
            ci_run_id=ci_run_id,
            ontology_categories=ontology_categories,
            split_manifest=manifest,
            known_limitations=limitations,
            iaa_seed=iaa_seed,
            iaa_resamples=iaa_resamples,
        )
    except ReleaseBlockedError as exc:
        _echo_gate_failures(exc.gate_results)
        return 1

    print(f"release {release_manifest.release_id!r} written: counts={release_manifest.counts}")
    return None


@app.command(name="render-dataset-card")
def render_dataset_card_command(
    *,
    data_root: Annotated[
        Path,
        Parameter(
            validator=cyclopts.validators.Path(exists=True, file_okay=False), help="data/segmenter/"
        ),
    ],
    release_id: str,
    output: Annotated[
        Path | None,
        Parameter(help="Where to write the card; defaults to <release dir>/dataset_card.md"),
    ] = None,
) -> None:
    """Render the RFC 0012 §15 dataset card for an already-built release."""
    store = SegmenterDatasetStore(data_root)
    manifest = store.read_release_manifest(release_id)
    card = render_dataset_card(manifest)
    destination = output or (store.release_dir(release_id) / "dataset_card.md")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(card, encoding="utf-8")
    print(f"wrote {destination}")


def _echo_gate_failures(gate_results: list[GateResult]) -> None:
    print("release blocked:", file=sys.stderr)
    for gate in gate_results:
        print(f"  [{gate.severity.value}] {gate.name}: {gate.detail}", file=sys.stderr)


if __name__ == "__main__":
    app()
