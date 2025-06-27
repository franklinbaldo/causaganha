"""
Models package for CausaGanha.

Contains dataclasses and interfaces for unified tribunal handling.
"""

from .diario import Diario
from .interfaces import DiarioDiscovery, DiarioDownloader, DiarioAnalyzer

__all__ = ["Diario", "DiarioDiscovery", "DiarioDownloader", "DiarioAnalyzer"]
