"""
Models package for CausaGanha.

Contains dataclasses and interfaces for unified tribunal handling.
"""

from .analytics import OutcomeTrend, RatingPoint, RatingTrend
from .diario import Diario
from .interfaces import DiarioAnalyzer, DiarioDiscovery, DiarioDownloader
from .llm_output import Decision, ExtractionResult

__all__ = [
    "Diario",
    "DiarioDiscovery",
    "DiarioDownloader",
    "DiarioAnalyzer",
    "Decision",
    "ExtractionResult",
    "OutcomeTrend",
    "RatingPoint",
    "RatingTrend",
]
