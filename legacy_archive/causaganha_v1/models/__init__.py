"""Models package for CausaGanha.

Contains dataclasses and interfaces for unified tribunal handling.
"""

from .diario import Diario
from .interfaces import DiarioAnalyzer, DiarioDiscovery, DiarioDownloader
from .llm_output import Decision, ExtractionResult


__all__ = [
    "Decision",
    "Diario",
    "DiarioAnalyzer",
    "DiarioDiscovery",
    "DiarioDownloader",
    "ExtractionResult",
]
