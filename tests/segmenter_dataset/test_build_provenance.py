from __future__ import annotations

import pytest
from pydantic import ValidationError

from segmenter_dataset.schemas import AnnotationQuality, ReleaseManifest


def test_release_manifest_requires_full_hashes_and_ci_identity() -> None:
    with pytest.raises(ValidationError):
        ReleaseManifest(
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="abc123",
            dependency_lock_hash="lock123",
            ci_provider="",
            ci_run_id="",
            split_manifest_hash="x",
            split_hashes={},
            document_resolutions={},
            annotation_quality=AnnotationQuality(),
            iaa_seed=1,
            iaa_resamples=1000,
            created_at="2026-01-01T00:00:00Z",
        )
