"""CLI for split assignment and immutable dataset release construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from segmenter_dataset.ontology import ONTOLOGY_V8, load_categories
from segmenter_dataset.release import ReleaseBlockedError, build_dataset_release
from segmenter_dataset.schemas import KnownLimitation, SplitManifest
from segmenter_dataset.splits import (
    GroupingKeys,
    assign_splits,
    build_groups,
    create_split_manifest,
    evaluation_eligible_document_ids,
    train_eligible_document_ids,
)
from segmenter_dataset.store import SegmenterDatasetStore


if TYPE_CHECKING:
    from segmenter_dataset.gates import GateResult


app = typer.Typer(no_args_is_help=True, help="Segmenter dataset lifecycle (RFC 0012).")


@app.command("assign-splits")
def assign_splits_command(
    data_root: Path = typer.Option(..., exists=True, file_okay=False, help="data/segmenter/"),
    output: Path = typer.Option(..., help="Where to write split_manifest.json"),
    train_ratio: float = typer.Option(0.70),
    val_ratio: float = typer.Option(0.15),
    seed: int = typer.Option(..., help="Deterministic assignment seed"),
    near_duplicate_threshold: float = typer.Option(0.9),
) -> None:
    """Group documents, apply role eligibility, and write a reproducible manifest."""
    store = SegmenterDatasetStore(data_root)
    documents = store.list_documents()
    annotations = store.list_annotations()
    reviews = store.list_reviews()
    grouping_keys = [GroupingKeys.from_document(document) for document in documents]
    groups = build_groups(
        documents,
        grouping_keys,
        near_duplicate_threshold=near_duplicate_threshold,
    )
    assignment = assign_splits(
        groups,
        train_eligible=train_eligible_document_ids(annotations),
        evaluation_eligible=evaluation_eligible_document_ids(reviews),
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        seed=seed,
    )
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
    typer.echo(
        f"wrote {output}: train={len(manifest.train_ids)} "
        f"val={len(manifest.val_ids)} test={len(manifest.test_ids)}"
    )


@app.command("build-release")
def build_release_command(
    data_root: Path = typer.Option(..., exists=True, file_okay=False, help="data/segmenter/"),
    split_manifest: Path = typer.Option(..., exists=True, help="Output of assign-splits"),
    release_id: str = typer.Option(...),
    label_space: Path = typer.Option(..., exists=True, help="Path to label_space.json"),
    source_commit: str = typer.Option(..., help="Full 40-character Git commit SHA"),
    dependency_lock_hash: str = typer.Option(..., help="SHA-256 of the pinned lockfile"),
    ci_provider: str = typer.Option(..., help="CI provider, e.g. github-actions"),
    ci_run_id: str = typer.Option(..., help="Immutable CI run identifier"),
    guideline_version: str = typer.Option(...),
    iaa_seed: int = typer.Option(...),
    iaa_resamples: int = typer.Option(1000, min=1000),
    known_limitations: Path | None = typer.Option(
        None, exists=True, help="JSON list of {gate, reason}"
    ),
    ontology_version: str = typer.Option(ONTOLOGY_V8),
) -> None:
    """Build the immutable dataset release."""
    store = SegmenterDatasetStore(data_root)
    manifest = SplitManifest.model_validate_json(split_manifest.read_text(encoding="utf-8"))
    limitations: list[KnownLimitation] = []
    if known_limitations is not None:
        raw = json.loads(known_limitations.read_text(encoding="utf-8"))
        limitations = [KnownLimitation(**entry) for entry in raw]

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
            ontology_categories=load_categories(label_space),
            split_manifest=manifest,
            known_limitations=limitations,
            iaa_seed=iaa_seed,
            iaa_resamples=iaa_resamples,
        )
    except ReleaseBlockedError as exc:
        _echo_gate_failures(exc.gate_results)
        raise typer.Exit(code=1) from exc

    typer.echo(f"release {release_manifest.release_id!r} written: counts={release_manifest.counts}")


def _echo_gate_failures(gate_results: list[GateResult]) -> None:
    typer.echo("release blocked:", err=True)
    for gate in gate_results:
        typer.echo(f"  [{gate.severity.value}] {gate.name}: {gate.detail}", err=True)


if __name__ == "__main__":
    app()
