"""
TJRO-specific diario analyzer adapter.

This adapter integrates the existing Gemini extractor
with the new Diario dataclass interface.
"""

import logging
from typing import List, Dict, Any
from models.interfaces import DiarioAnalyzer
from models.diario import Diario
from extractor import GeminiExtractor


class TJROAnalyzer(DiarioAnalyzer):
    """TJRO-specific diario analyzer using existing Gemini extraction."""
    
    def __init__(self):
        """Initialize with the existing Gemini extractor."""
        self.extractor = GeminiExtractor()
    
    def extract_decisions(self, diario: Diario) -> List[Dict[str, Any]]:
        """
        Extract judicial decisions from diario PDF.
        
        This uses the existing GeminiExtractor but adapts the output
        to the standardized format expected by the interface.
        """
        if not diario.pdf_path or not diario.pdf_path.exists():
            raise ValueError(f"PDF file not found for {diario.display_name}")
        
        logging.info(f"Extracting decisions from {diario.display_name}")
        
        try:
            # Use the existing extractor
            raw_decisions = self.extractor.extract_decisions_from_pdf(str(diario.pdf_path))
            
            # Standardize the decision format
            standardized_decisions = []
            
            for decision in raw_decisions:
                standardized_decision = self._standardize_decision(decision, diario)
                standardized_decisions.append(standardized_decision)
            
            logging.info(f"Extracted {len(standardized_decisions)} decisions from {diario.display_name}")
            return standardized_decisions
            
        except Exception as e:
            logging.error(f"Error extracting decisions from {diario.display_name}: {e}")
            # Return empty list instead of raising to allow processing to continue
            return []
    
    def _standardize_decision(self, raw_decision: Dict[str, Any], diario: Diario) -> Dict[str, Any]:
        """
        Convert raw extractor output to standardized decision format.
        
        The existing extractor may return decisions in various formats.
        This method ensures consistency across all decisions.
        """
        standardized = {
            'numero_processo': raw_decision.get('numero_processo', ''),
            'polo_ativo': raw_decision.get('polo_ativo', []),
            'polo_passivo': raw_decision.get('polo_passivo', []),
            'resultado': raw_decision.get('resultado', ''),
            'data_decisao': diario.data.isoformat(),  # Use diario date as default
            'tribunal': diario.tribunal,
            'source_url': diario.url,
            'ia_identifier': diario.ia_identifier,
        }
        
        # Handle different field names that might exist in raw data
        field_mappings = {
            'process_number': 'numero_processo',
            'active_party': 'polo_ativo',
            'passive_party': 'polo_passivo',
            'decision': 'resultado',
            'outcome': 'resultado',
            'decision_date': 'data_decisao',
            'advogados_ativo': 'polo_ativo',
            'advogados_passivo': 'polo_passivo',
        }
        
        for raw_key, std_key in field_mappings.items():
            if raw_key in raw_decision and raw_decision[raw_key]:
                standardized[std_key] = raw_decision[raw_key]
        
        # Ensure lawyer lists are properly formatted
        if isinstance(standardized['polo_ativo'], str):
            standardized['polo_ativo'] = [standardized['polo_ativo']]
        if isinstance(standardized['polo_passivo'], str):
            standardized['polo_passivo'] = [standardized['polo_passivo']]
        
        # Add any additional metadata from raw decision
        standardized['raw_data'] = raw_decision
        
        return standardized
    
    def analyze_diario(self, diario: Diario) -> Diario:
        """
        Analyze diario and update with extracted decisions.
        
        This extends the base implementation to add TJRO-specific
        metadata and validation.
        """
        if diario.tribunal != 'tjro':
            raise ValueError(f"TJROAnalyzer cannot handle tribunal: {diario.tribunal}")
        
        # Call the parent implementation
        diario = super().analyze_diario(diario)
        
        # Add TJRO-specific analysis metadata
        decisions = diario.metadata.get('decisions', [])
        
        # Calculate TJRO-specific statistics
        tjro_stats = {
            'total_processes': len(decisions),
            'unique_processes': len(set(d.get('numero_processo', '') for d in decisions if d.get('numero_processo'))),
            'results_breakdown': {},
            'lawyer_count': {
                'ativo': 0,
                'passivo': 0
            }
        }
        
        # Analyze results and lawyers
        for decision in decisions:
            resultado = decision.get('resultado', 'unknown')
            tjro_stats['results_breakdown'][resultado] = tjro_stats['results_breakdown'].get(resultado, 0) + 1
            
            polo_ativo = decision.get('polo_ativo', [])
            polo_passivo = decision.get('polo_passivo', [])
            
            tjro_stats['lawyer_count']['ativo'] += len(polo_ativo) if isinstance(polo_ativo, list) else 1 if polo_ativo else 0
            tjro_stats['lawyer_count']['passivo'] += len(polo_passivo) if isinstance(polo_passivo, list) else 1 if polo_passivo else 0
        
        diario.metadata['tjro_analysis'] = tjro_stats
        
        logging.info(f"TJRO analysis complete for {diario.display_name}: "
                    f"{tjro_stats['total_processes']} decisions, "
                    f"{tjro_stats['unique_processes']} unique processes")
        
        return diario