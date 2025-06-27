"""
Abstract interfaces for tribunal-specific implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date
from .diario import Diario


class DiarioDiscovery(ABC):
    """Abstract interface for discovering diario URLs from tribunal websites."""
    
    @abstractmethod
    def get_diario_url(self, target_date: date) -> Optional[str]:
        """
        Get diario URL for specific date.
        
        Args:
            target_date: The date to search for
            
        Returns:
            URL string if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_latest_diario_url(self) -> Optional[str]:
        """
        Get URL for the most recent available diario.
        
        Returns:
            URL string if found, None otherwise
        """
        pass
    
    def list_diarios_in_range(self, start_date: date, end_date: date) -> List[str]:
        """
        Get URLs for all diarios in date range.
        
        Default implementation calls get_diario_url for each date.
        Tribunals can override for more efficient batch discovery.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            
        Returns:
            List of URL strings found in the range
        """
        urls = []
        current = start_date
        while current <= end_date:
            url = self.get_diario_url(current)
            if url:
                urls.append(url)
            # Move to next day
            from datetime import timedelta
            current = current + timedelta(days=1)
        return urls
    
    @property
    @abstractmethod
    def tribunal_code(self) -> str:
        """Return the tribunal code (e.g., 'tjro', 'tjsp')."""
        pass


class DiarioDownloader(ABC):
    """Abstract interface for downloading diario PDFs."""
    
    @abstractmethod
    def download_diario(self, diario: Diario) -> Diario:
        """
        Download PDF and update diario with local path.
        
        Args:
            diario: Diario object with URL to download
            
        Returns:
            Updated Diario with pdf_path set and status updated
        """
        pass
    
    @abstractmethod
    def archive_to_ia(self, diario: Diario) -> Diario:
        """
        Archive to Internet Archive and update IA identifier.
        
        Args:
            diario: Diario object with local PDF file
            
        Returns:
            Updated Diario with ia_identifier set
        """
        pass
    
    def download_and_archive(self, diario: Diario) -> Diario:
        """
        Convenience method to download and archive in one step.
        
        Args:
            diario: Diario object to process
            
        Returns:
            Fully processed Diario with both local and IA paths
        """
        diario = self.download_diario(diario)
        if diario.pdf_path and diario.pdf_path.exists():
            diario = self.archive_to_ia(diario)
        return diario


class DiarioAnalyzer(ABC):
    """Abstract interface for analyzing diario content."""
    
    @abstractmethod
    def extract_decisions(self, diario: Diario) -> List[Dict[str, Any]]:
        """
        Extract judicial decisions from diario PDF.
        
        Args:
            diario: Diario object with pdf_path set
            
        Returns:
            List of decision dictionaries with standardized fields:
            - numero_processo: Process number
            - polo_ativo: Active party lawyers
            - polo_passivo: Passive party lawyers  
            - resultado: Decision outcome
            - data_decisao: Decision date
            - tribunal: Source tribunal
        """
        pass
    
    def analyze_diario(self, diario: Diario) -> Diario:
        """
        Analyze diario and update with extracted decisions.
        
        Args:
            diario: Diario object to analyze
            
        Returns:
            Updated Diario with analysis results in metadata
        """
        if not diario.pdf_path or not diario.pdf_path.exists():
            raise ValueError(f"PDF file not found for {diario.display_name}")
        
        decisions = self.extract_decisions(diario)
        diario.metadata['decisions'] = decisions
        diario.metadata['decision_count'] = len(decisions)
        diario.update_status('analyzed')
        
        return diario


class TribunalAdapter(ABC):
    """
    Combined interface for a complete tribunal implementation.
    
    This provides a unified interface that combines discovery, download,
    and analysis capabilities for a specific tribunal.
    """
    
    @property
    @abstractmethod
    def discovery(self) -> DiarioDiscovery:
        """Get the discovery implementation for this tribunal."""
        pass
    
    @property
    @abstractmethod
    def downloader(self) -> DiarioDownloader:
        """Get the downloader implementation for this tribunal."""
        pass
    
    @property
    @abstractmethod
    def analyzer(self) -> DiarioAnalyzer:
        """Get the analyzer implementation for this tribunal."""
        pass
    
    @property
    @abstractmethod
    def tribunal_code(self) -> str:
        """Return the tribunal code."""
        pass
    
    def create_diario(self, target_date: date) -> Optional[Diario]:
        """
        Create a Diario object for the given date.
        
        Args:
            target_date: Date to create diario for
            
        Returns:
            Diario object if URL found, None otherwise
        """
        url = self.discovery.get_diario_url(target_date)
        if not url:
            return None
        
        from pathlib import Path
        filename = Path(url).name
        
        return Diario(
            tribunal=self.tribunal_code,
            data=target_date,
            url=url,
            filename=filename
        )
    
    def process_diario(self, diario: Diario, download: bool = True, 
                      archive: bool = True, analyze: bool = True) -> Diario:
        """
        Complete processing pipeline for a diario.
        
        Args:
            diario: Diario to process
            download: Whether to download PDF
            archive: Whether to archive to IA
            analyze: Whether to analyze content
            
        Returns:
            Fully processed Diario
        """
        if download:
            diario = self.downloader.download_diario(diario)
        
        if archive and diario.pdf_path:
            diario = self.downloader.archive_to_ia(diario)
        
        if analyze and diario.pdf_path:
            diario = self.analyzer.analyze_diario(diario)
        
        return diario