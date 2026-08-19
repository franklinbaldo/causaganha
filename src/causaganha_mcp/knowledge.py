"""Typed OKF knowledge consumed by the MCP product surface."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from okf_parser import load_bundle


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_ROOT = _REPOSITORY_ROOT / "knowledge"
_SPEC_TEMPLATE = ".okf/specs/{slug}.schema.sql"


class PipelineMetadata(BaseModel):
    """Stable metadata authored in the OKF ``Pipeline`` relation."""

    nome: str = Field(min_length=1)
    fonte: str = Field(min_length=1)
    pacote: str = Field(min_length=1)
    mcp_status: str = Field(min_length=1)


def load_pipeline_metadata(root: Path = _KNOWLEDGE_ROOT) -> tuple[PipelineMetadata, ...]:
    """Load the declared ``Pipeline`` relation as typed in-process metadata.

    Knowledge-loading failures are intentionally fatal for the aggregate status
    surface: silently falling back to a second hard-coded pipeline catalog would
    make the OKF relation decorative and could return stale product metadata.
    Individual pipeline data/manifest failures remain partial results in
    ``tools.status`` as before.
    """
    bundle = load_bundle(root)
    if not bundle.is_conformant:
        raise RuntimeError("knowledge bundle is not OKF-conformant")

    with bundle.compile_types(_SPEC_TEMPLATE) as typed:
        if "Pipeline" not in typed.tables:
            raise RuntimeError("knowledge bundle has no declared Pipeline relation")
        rows = typed["Pipeline"].execute().to_dict(orient="records")

    metadata = tuple(PipelineMetadata.model_validate(row) for row in rows)
    if not metadata:
        raise RuntimeError("knowledge Pipeline relation is empty")
    return metadata
