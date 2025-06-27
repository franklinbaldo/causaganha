"""
Complete TJRO tribunal adapter.

This provides a unified interface for all TJRO operations
using the new Diario dataclass system.
"""

from models.interfaces import TribunalAdapter, DiarioDiscovery, DiarioDownloader, DiarioAnalyzer
from .discovery import TJRODiscovery
from .download_adapter import TJRODownloader
from .analyze_adapter import TJROAnalyzer


class TJROAdapter(TribunalAdapter):
    """Complete TJRO tribunal implementation."""
    
    def __init__(self):
        """Initialize all TJRO components."""
        self._discovery = TJRODiscovery()
        self._downloader = TJRODownloader()
        self._analyzer = TJROAnalyzer()
    
    @property
    def tribunal_code(self) -> str:
        """Return the tribunal code."""
        return "tjro"
    
    @property
    def discovery(self) -> DiarioDiscovery:
        """Get the discovery implementation for TJRO."""
        return self._discovery
    
    @property
    def downloader(self) -> DiarioDownloader:
        """Get the downloader implementation for TJRO."""
        return self._downloader
    
    @property
    def analyzer(self) -> DiarioAnalyzer:
        """Get the analyzer implementation for TJRO."""
        return self._analyzer