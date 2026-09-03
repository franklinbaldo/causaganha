"""Record schemas for the segmenter dataset lifecycle (RFC 0012 §8).

Three artifact types that coexist per document (RFC 0012 §3.1) — a document
record is never edited or replaced; each annotation and each review is an
additional record referencing it, never an overwrite:

- :class:`DocumentRecord` — immutable source text + provenance.
- :class:`AnnotationRecord` — one annotator's complete labeling of a
  document, plus which ontology categories it actually considered
  (``covered_categories`` — RFC 0012 §5.1's false-negative guard).
- :class:`ReviewRecord` — adjudication of one or more annotations,
  referencing them explicitly by ``annotation_id`` (RFC 0012 §8's lineage
  fix — a review never just references a bare ``document_id``).

:class:`ReleaseManifest` is the dataset-level artifact (§3.1: split-assigned
and released are properties of a *build*, not of a document) produced by
``release.build_dataset_release``.

Pydantic validates shape and type here; the semantic/mechanical invariants
of RFC 0012 §11 (offset bounds, pair balance, ontology membership, ...) are
a separate concern in :mod:`segmenter_dataset.mechanical`, per RFC 0012
§3.2 — mechanical validity is not semantic correctness, and neither layer
should quietly absorb the other's job.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


# RFC 0012 §5.3/§9 — an accepted review must resolve at least two
# independent annotations.
MIN_INDEPENDENT_ANNOTATIONS = 2


class Label(BaseModel):
    """One span label — ``text[start:end]`` tagged ``category``."""

    model_config = ConfigDict(frozen=True)

    start: int
    end: int
    category: str

    @model_validator(mode="after")
    def _check_order(self) -> Label:
        if not (0 <= self.start < self.end):
            msg = (
                "label offsets must satisfy 0 <= start < end, got "
                f"start={self.start} end={self.end}"
            )
            raise ValueError(msg)
        return self


class SourceInfo(BaseModel):
    """Where a document came from (RFC 0012 §8)."""

    model_config = ConfigDict(frozen=True)

    system: str
    tribunal: str
    document_type: str
    source_uri: str
    source_hash: str


class GroupingInfo(BaseModel):
    """Stable keys that keep a related-document group from crossing splits (RFC 0012 §10).

    All fields are optional and default to unset — an ingestion pipeline
    with access to structured source metadata (e.g. JURIS/DJEN's own
    process-linkage fields) populates ``source_process_id``,
    ``document_family``, and ``parent_document_id`` directly, since none of
    those are recoverable from the document's own text.
    ``normalized_process_number`` is the one field this module can also
    derive on its own when unset — see
    :func:`segmenter_dataset.provenance.extract_normalized_process_number`
    and :meth:`segmenter_dataset.splits.GroupingKeys.from_document`.
    """

    model_config = ConfigDict(frozen=True)

    normalized_process_number: str | None = None
    source_process_id: str | None = None
    document_family: str | None = None
    parent_document_id: str | None = None


class ExtractionInfo(BaseModel):
    """Which heuristic extractor produced ``proposed_labels`` (RFC 0012 §8)."""

    model_config = ConfigDict(frozen=True)

    method: str
    version: str


class DocumentRecord(BaseModel):
    """Immutable source-text record (RFC 0012 §8 "Registro de documento").

    Never edited after creation — ``document_id`` is content-addressed
    (:func:`segmenter_dataset.ids.document_id`) from ``source``, so two
    extraction passes over the same source document resolve to the same
    record rather than minting a new identity per extractor run.
    """

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(pattern=r"^doc_[0-9a-f]{32}$")
    text: str
    proposed_labels: list[Label] = Field(default_factory=list)
    source: SourceInfo
    extraction: ExtractionInfo
    grouping: GroupingInfo = Field(default_factory=GroupingInfo)


class AnnotatorConfig(BaseModel):
    """Identity of the annotator run that produced an :class:`AnnotationRecord`."""

    model_config = ConfigDict(frozen=True)

    model_family: str
    guideline_version: str
    seeded_with: str = "none"


class AnnotationRecord(BaseModel):
    """One annotator's complete labeling of a document (RFC 0012 §8).

    ``covered_categories`` is the RFC 0012 §5.1 false-negative guard: it is
    the subset of the ontology this annotator actually considered. A
    category outside this set must be masked out of training loss/support
    for this document (§5.1), never read as a negative example.
    """

    model_config = ConfigDict(frozen=True)

    annotation_id: str = Field(pattern=r"^ann_[0-9a-f]{32}$")
    document_id: str = Field(pattern=r"^doc_[0-9a-f]{32}$")
    annotator_id: str
    annotator_config: AnnotatorConfig
    ontology_version: str
    covered_categories: tuple[str, ...]
    labels: list[Label] = Field(default_factory=list)
    allowed_unmatched: dict[str, str] = Field(default_factory=dict)
    completed_at: str
    annotation_method: str

    @model_validator(mode="after")
    def _labels_within_covered_categories(self) -> AnnotationRecord:
        uncovered = {label.category for label in self.labels} - set(self.covered_categories)
        if uncovered:
            msg = (
                f"labels use categories outside covered_categories: {sorted(uncovered)} — "
                "an annotator cannot produce a label for a category it wasn't asked to consider"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _allowed_unmatched_has_reasons(self) -> AnnotationRecord:
        blank_reasons = sorted(
            category for category, reason in self.allowed_unmatched.items() if not reason.strip()
        )
        if blank_reasons:
            msg = f"allowed_unmatched requires a non-empty reason: {blank_reasons}"
            raise ValueError(msg)
        return self

    def is_independent_capable(self) -> bool:
        """RFC 0012 §5.3: an annotation counts as independent only if unseeded.

        This checks the necessary local condition (``seeded_with == "none"``)
        — the full definition also requires distinct model families *or*
        provably isolated runs across a *pair* of annotations, which is a
        property of two records together, not one (see
        :func:`segmenter_dataset.mechanical.annotations_are_independent`).
        """
        return self.annotator_config.seeded_with == "none"


class ReviewRecord(BaseModel):
    """Adjudication of one or more annotations (RFC 0012 §8 "Registro de review").

    ``input_annotation_ids`` names exactly which annotation records this
    review resolved — never just ``document_id``, because a document may
    accumulate more than two annotations over time and a reconstructed
    release must be able to tell which pair a given review adjudicated
    (RFC 0012 §8's lineage fix).
    """

    model_config = ConfigDict(frozen=True)

    review_id: str = Field(pattern=r"^rev_[0-9a-f]{32}$")
    document_id: str = Field(pattern=r"^doc_[0-9a-f]{32}$")
    input_annotation_ids: tuple[str, ...]
    status: str
    final_labels: list[Label] = Field(default_factory=list)
    allowed_unmatched: dict[str, str] = Field(default_factory=dict)
    reviewers: tuple[str, ...]
    resolution: str
    notes: tuple[str, ...] = ()
    approved_at: str

    @model_validator(mode="after")
    def _at_least_two_inputs_when_accepted(self) -> ReviewRecord:
        n_inputs = len(self.input_annotation_ids)
        if self.status == "accepted" and n_inputs < MIN_INDEPENDENT_ANNOTATIONS:
            msg = (
                "an accepted review must resolve at least two independent annotations "
                f"(RFC 0012 §9); got {n_inputs}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _allowed_unmatched_has_reasons(self) -> ReviewRecord:
        blank_reasons = sorted(
            category for category, reason in self.allowed_unmatched.items() if not reason.strip()
        )
        if blank_reasons:
            msg = f"allowed_unmatched requires a non-empty reason: {blank_reasons}"
            raise ValueError(msg)
        return self


class KnownLimitation(BaseModel):
    """A waivable/advisory gate recorded as a lightweight known limitation.

    RFC 0012 §12/§12.1: no formal ``approved_by``/expiry object — the next
    major release is the natural review point (§13.1), not a hardcoded
    expiry field.
    """

    model_config = ConfigDict(frozen=True)

    gate: str
    status: str = "known_limitation"
    reason: str


class SplitManifest(BaseModel):
    """Reproducible split-assignment artifact consumed by the release builder."""

    model_config = ConfigDict(frozen=True)

    train_ids: tuple[str, ...]
    val_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    seed: int
    train_ratio: float
    val_ratio: float
    near_duplicate_threshold: float
    groups: dict[str, tuple[str, ...]]

    @model_validator(mode="after")
    def _validate_ratios(self) -> SplitManifest:
        if not (0 < self.train_ratio < 1 and 0 < self.val_ratio < 1):
            message = "train_ratio and val_ratio must be between 0 and 1"
            raise ValueError(message)
        if self.train_ratio + self.val_ratio >= 1:
            message = "train_ratio + val_ratio must be < 1"
            raise ValueError(message)
        if not (0 <= self.near_duplicate_threshold <= 1):
            message = "near_duplicate_threshold must be in [0, 1]"
            raise ValueError(message)
        return self


class AnnotationQuality(BaseModel):
    """IAA evidence required by RFC 0012 §8/§14 — never a bare number."""

    model_config = ConfigDict(frozen=True)

    val_iaa_span_f1: float | None = None
    val_iaa_span_f1_ci95_low: float | None = None
    test_iaa_span_f1: float | None = None
    test_iaa_span_f1_ci95_low: float | None = None
    per_category_iaa: dict[str, float] = Field(default_factory=dict)
    unreliable_eval_categories: tuple[str, ...] = ()


class ReleaseManifest(BaseModel):
    """Dataset-level release artifact (RFC 0012 §8, §12).

    Lives at ``dataset-releases/<release_id>/manifest.csv`` (plus companion
    tables — see ``store.write_release_manifest_tables``) once
    ``release.build_dataset_release`` finishes. ``document_resolutions``
    pins the exact ``annotation_id``/``review_id`` used per document per
    split — without it, rebuilding from the same ``document_id`` set could
    silently pick a different annotation if the document was re-annotated
    between builds (RFC 0012 §8's lineage fix). ``split_manifest_hash`` and
    ``ci_provider``/``ci_run_id`` additionally pin the exact split and CI
    run a release came from, for reproducibility.
    """

    model_config = ConfigDict(frozen=True)

    release_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    ontology_version: str
    guideline_version: str
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    dependency_lock_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    ci_provider: str
    ci_run_id: str
    split_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_hashes: dict[str, str]
    document_resolutions: dict[str, dict[str, str]]
    counts: dict[str, int] = Field(default_factory=dict)
    tribunals: dict[str, int] = Field(default_factory=dict)
    document_types: dict[str, int] = Field(default_factory=dict)
    annotation_quality: AnnotationQuality
    iaa_seed: int
    iaa_resamples: int
    known_limitations: tuple[KnownLimitation, ...] = ()
    created_at: str


class CheckpointSelection(BaseModel):
    """Outcome of RFC 0012 §5 point 5's checkpoint-selection rule.

    ``rule`` is fixed prose rather than a free-form field, so a manifest
    cannot quietly redefine the selection rule after the fact — it exists
    to be compared against, not edited per run.
    """

    model_config = ConfigDict(frozen=True)

    rule: str = (
        "primary: highest validation macro-F1 over trainable categories; "
        "tie-break 1: lowest epoch; tie-break 2: lowest validation loss"
    )
    selected_epoch: int
    val_macro_f1: float
    val_loss: float | None = None
    per_epoch_val_macro_f1: dict[int, float] = Field(default_factory=dict)


class ExperimentManifest(BaseModel):
    """One training run against a frozen dataset release export (RFC 0012 §13/§15 PR3).

    Written once training finishes and a checkpoint is selected — before any
    test data is touched. This is what lets a later, separately-gated test
    evaluation (RFC 0012 §3.3/§13.1) point at an already-frozen configuration
    instead of a moving target.
    """

    model_config = ConfigDict(frozen=True)

    experiment_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    release_id: str
    ontology_version: str
    guideline_version: str
    seed: int
    dependency_lock_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    epochs: int
    batch_size: int
    device: str
    checkpoint_dir: str
    checkpoint_selection: CheckpointSelection
    created_at: str
    # #1048: ties a manifest to the exact bytes/environment a run used, not
    # just to a release/device *name* that could point at different content.
    dataset_export_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    opf_version: str | None = None
    hardware: str | None = None
    finetune_summary_path: str | None = None


class ModelAcceptanceEvidence(BaseModel):
    """RFC 0012 §16.2 gate evidence — the numbers a model card must show, never a bare F1."""

    model_config = ConfigDict(frozen=True)

    macro_f1_model: float | None
    macro_f1_baseline: float | None
    baseline_diff_ci95_low: float | None
    beats_baseline: bool
    critical_category_f1: dict[str, float]
    critical_categories_passed: bool
    eligible_for_deploy: bool
    bootstrap_seed: int
    bootstrap_resamples: int


class ModelCard(BaseModel):
    """Model-release artifact (RFC 0012 §16.2) — distinct from a dataset's ReleaseManifest.

    ``release_id`` here is the model-release id (``segmenter-model-vX.Y``),
    separate from ``dataset_release_id`` (``segmenter-real-vX.Y``) — §16.2's
    explicit point that dataset acceptance and model acceptance are versioned,
    and can be accepted, independently.
    """

    model_config = ConfigDict(frozen=True)

    release_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    dataset_release_id: str
    experiment_id: str
    test_release_used: str
    test_unlocked_at: str
    test_unlocked_by: str
    test_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    acceptance: ModelAcceptanceEvidence
    intended_use: str
    known_limitations: tuple[str, ...] = ()
    created_at: str
