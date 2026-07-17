"""Record schemas for the segmenter dataset lifecycle (RFC 0012 §8)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
            message = (
                "label offsets must satisfy 0 <= start < end, "
                f"got start={self.start} end={self.end}"
            )
            raise ValueError(message)
        return self


class SourceInfo(BaseModel):
    """Where a document came from."""

    model_config = ConfigDict(frozen=True)

    system: str
    tribunal: str
    document_type: str
    source_uri: str
    source_hash: str


class GroupingInfo(BaseModel):
    """Stable keys used to prevent related documents crossing splits."""

    model_config = ConfigDict(frozen=True)

    normalized_process_number: str | None = None
    source_process_id: str | None = None
    document_family: str | None = None
    parent_document_id: str | None = None


class ExtractionInfo(BaseModel):
    """Which heuristic extractor produced ``proposed_labels``."""

    model_config = ConfigDict(frozen=True)

    method: str
    version: str


class DocumentRecord(BaseModel):
    """Immutable source-text record."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(pattern=r"^doc_[0-9a-f]{32}$")
    text: str
    proposed_labels: list[Label] = Field(default_factory=list)
    source: SourceInfo
    extraction: ExtractionInfo
    grouping: GroupingInfo = Field(default_factory=GroupingInfo)


class AnnotatorConfig(BaseModel):
    """Identity of the annotator run that produced an annotation."""

    model_config = ConfigDict(frozen=True)

    model_family: str
    guideline_version: str
    seeded_with: str = "none"


class AnnotationRecord(BaseModel):
    """One annotator's complete labeling of a document."""

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
    def _validate_annotation_contract(self) -> AnnotationRecord:
        covered = set(self.covered_categories)
        uncovered = {label.category for label in self.labels} - covered
        if uncovered:
            message = f"labels use categories outside covered_categories: {sorted(uncovered)}"
            raise ValueError(message)
        blank_reasons = sorted(
            base for base, reason in self.allowed_unmatched.items() if not reason.strip()
        )
        if blank_reasons:
            message = f"allowed_unmatched requires a non-empty reason: {blank_reasons}"
            raise ValueError(message)
        return self

    def is_independent_capable(self) -> bool:
        """Return whether local metadata permits independent use."""
        return (
            self.annotator_config.seeded_with == "none"
            and self.annotation_method == "independent_full_read"
        )


class ReviewRecord(BaseModel):
    """Adjudication of explicit annotation records."""

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
    def _validate_review_contract(self) -> ReviewRecord:
        if self.status == "accepted":
            unique_inputs = set(self.input_annotation_ids)
            if len(unique_inputs) < MIN_INDEPENDENT_ANNOTATIONS:
                message = "an accepted review must resolve at least two distinct annotations"
                raise ValueError(message)
            if len(unique_inputs) != len(self.input_annotation_ids):
                message = "input_annotation_ids must not contain duplicates"
                raise ValueError(message)
        blank_reasons = sorted(
            base for base, reason in self.allowed_unmatched.items() if not reason.strip()
        )
        if blank_reasons:
            message = f"allowed_unmatched requires a non-empty reason: {blank_reasons}"
            raise ValueError(message)
        return self


class KnownLimitation(BaseModel):
    """A waivable advisory gate recorded in the release manifest."""

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
    """IAA evidence required by RFC 0012 §8/§14."""

    model_config = ConfigDict(frozen=True)

    val_iaa_span_f1: float | None = None
    val_iaa_span_f1_ci95_low: float | None = None
    test_iaa_span_f1: float | None = None
    test_iaa_span_f1_ci95_low: float | None = None
    per_category_iaa: dict[str, float] = Field(default_factory=dict)
    unreliable_eval_categories: tuple[str, ...] = ()


class ReleaseManifest(BaseModel):
    """Dataset-level immutable release artifact."""

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
