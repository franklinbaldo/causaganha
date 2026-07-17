"""CLI entry point for the segmenter dataset lifecycle (RFC 0012).

Two commands, split at the same seam as RFC 0012 §10/§12:

- ``assign-splits`` — groups documents, applies role eligibility, and writes
  a ``split_manifest.json`` (RFC 0012 §8's intermediate, not-yet-a-release
  artifact).
- ``build-release`` — reads a ``split_manifest.json`` and runs
  ``build_dataset_release`` (RFC 0012 §12), writing the final immutable
  release manifest.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from segmenter_dataset.ontology import ONTOLOGY_V8, load_categories
from segmenter_dataset.release import ReleaseBlockedError, build_dataset_release
from segmenter_dataset.schemas import KnownLimitation
from segmenter_dataset.splits import (
    GroupingKeys,
    SplitAssignment,
    assign_splits,
    build_groups,
    evaluation_eligible_document_ids,
    train_eligible_document_ids,
)
from segmenter_dataset.store import SegmenterDatasetStore


if TYPE_CHECKING:
    # Path stays a live import above — Typer's @app.command parameters below
    # need a runtime-resolvable annotation to build the CLI schema.
    # GateResult is only used in a plain helper, not a command, so it's safe
    # to defer.
    from segmenter_dataset.gates import GateResult


app = typer.Typer(no_args_is_help=True, help="Segmenter dataset lifecycle (RFC 0012).")


@app.command("assign-splits")
def assign_splits_command(
    data_root: Path = typer.Option(..., exists=True, file_okay=False, help="data/segmenter/"),
    output: Path = typer.Option(..., help="Where to write split_manifest.json"),
    train_ratio: float = typer.Option(0.70),
    val_ratio: float = typer.Option(0.15),
    seed: int = typer.Option(..., help="Deterministic assignment seed (RFC 0012 §10)"),
    near_duplicate_threshold: float = typer.Option(0.9),
) -> None:
    """Group documents, apply role eligibility, and write a split manifest."""
    store = SegmenterDatasetStore(data_root)
    documents = store.list_documents()
    annotations = store.list_annotations()
    reviews = store.list_reviews()

    grouping_keys = [GroupingKeys(document_id=doc.document_id) for doc in documents]
    groups = build_groups(
        documents, grouping_keys, near_duplicate_threshold=near_duplicate_threshold
    )

    assignment = assign_splits(
        groups,
        train_eligible=train_eligible_document_ids(annotations),
        evaluation_eligible=evaluation_eligible_document_ids(reviews),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "train_ids": sorted(assignment.train_ids),
                "val_ids": sorted(assignment.val_ids),
                "test_ids": sorted(assignment.test_ids),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    typer.echo(
        f"wrote {output}: train={len(assignment.train_ids)} "
        f"val={len(assignment.val_ids)} test={len(assignment.test_ids)}"
    )


@app.command("build-release")
def build_release_command(
    data_root: Path = typer.Option(..., exists=True, file_okay=False, help="data/segmenter/"),
    split_manifest: Path = typer.Option(..., exists=True, help="Output of assign-splits"),
    release_id: str = typer.Option(...),
    label_space: Path = typer.Option(..., exists=True, help="Path to label_space.json"),
    source_commit: str = typer.Option(...),
    dependency_lock_hash: str = typer.Option(...),
    guideline_version: str = typer.Option(...),
    iaa_seed: int = typer.Option(...),
    known_limitations: Path | None = typer.Option(
        None, exists=True, help="JSON list of {gate, reason}"
    ),
    ontology_version: str = typer.Option(ONTOLOGY_V8),
) -> None:
    """Build the immutable dataset release (RFC 0012 §12)."""
    store = SegmenterDatasetStore(data_root)
    split_data = json.loads(split_manifest.read_text(encoding="utf-8"))
    assignment = SplitAssignment(
        train_ids=frozenset(split_data["train_ids"]),
        val_ids=frozenset(split_data["val_ids"]),
        test_ids=frozenset(split_data["test_ids"]),
    )

    limitations: list[KnownLimitation] = []
    if known_limitations is not None:
        raw = json.loads(known_limitations.read_text(encoding="utf-8"))
        limitations = [KnownLimitation(**entry) for entry in raw]

    ontology_categories = load_categories(label_space)

    try:
        manifest = build_dataset_release(
            store,
            release_id=release_id,
            ontology_version=ontology_version,
            guideline_version=guideline_version,
            source_commit=source_commit,
            dependency_lock_hash=dependency_lock_hash,
            ontology_categories=ontology_categories,
            split_assignment=assignment,
            known_limitations=limitations,
            iaa_seed=iaa_seed,
        )
    except ReleaseBlockedError as exc:
        _echo_gate_failures(exc.gate_results)
        raise typer.Exit(code=1) from exc

    typer.echo(f"release {manifest.release_id!r} written: counts={manifest.counts}")


def _echo_gate_failures(gate_results: list[GateResult]) -> None:
    typer.echo("release blocked:", err=True)
    for gate in gate_results:
        typer.echo(f"  [{gate.severity.value}] {gate.name}: {gate.detail}", err=True)


if __name__ == "__main__":
    app()
