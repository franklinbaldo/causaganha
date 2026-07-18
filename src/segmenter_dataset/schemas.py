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

    document_id: str
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

    annotation_id: str
    document_id: str
    annotator_id: str
    annotator_config: AnnotatorConfig
    ontology_version: str
    covered_categories: tuple[str, ...]
    labels: list[Label] = Field(default_factory=list)
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

    review_id: str
    document_id: str
    input_annotation_ids: tuple[str, ...]
    status: str
    final_labels: list[Label] = Field(default_factory=list)
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

    Lives at ``dataset-releases/<release_id>/manifest.json`` once
    ``release.build_dataset_release`` finishes. ``document_resolutions``
    pins the exact ``annotation_id``/``review_id`` used per document per
    split — without it, rebuilding from the same ``document_id`` set could
    silently pick a different annotation if the document was re-annotated
    between builds (RFC 0012 §8's lineage fix).
    """

    model_config = ConfigDict(frozen=True)

    release_id: str
    ontology_version: str
    guideline_version: str
    source_commit: str
    dependency_lock_hash: str
    split_hashes: dict[str, str]
    document_resolutions: dict[str, dict[str, str]]
    counts: dict[str, int] = Field(default_factory=dict)
    tribunals: dict[str, int] = Field(default_factory=dict)
    document_types: dict[str, int] = Field(default_factory=dict)
    annotation_quality: AnnotationQuality
    known_limitations: tuple[KnownLimitation, ...] = ()
    created_at: str
