"""Acquisition primitives for the TSE Processual open-data corpus."""

from .acquisition import DownloadEvidence, download_official_zip, validate_official_url
from .catalog import PROCESSUAL_2026_RESOURCES, ResourceKind, ResourceSpec

__all__ = [
    "PROCESSUAL_2026_RESOURCES",
    "DownloadEvidence",
    "ResourceKind",
    "ResourceSpec",
    "download_official_zip",
    "validate_official_url",
]
