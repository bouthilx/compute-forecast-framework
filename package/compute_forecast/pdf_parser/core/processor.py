"""Optimized PDF processor with split strategy orchestration."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from compute_forecast.pdf_parser.core.base_extractor import BaseExtractor
from compute_forecast.pdf_parser.core.validation import AffiliationValidator
from compute_forecast.pdf_parser.core.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class OptimizedPDFProcessor:
    """PDF processor that orchestrates multiple extraction methods using split strategy."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the processor with configuration.
        
        Args:
            config: Configuration dictionary for the processor
        """
        self.extractors = {}  # Will store {name: {'extractor': BaseExtractor, 'level': int}}
        self.config = config
        self.validator = AffiliationValidator()
        self.cost_tracker = CostTracker()
    
    def register_extractor(self, name: str, extractor: BaseExtractor, level: int) -> None:
        """Register an extractor with its priority level.
        
        Args:
            name: Unique name for the extractor
            extractor: BaseExtractor implementation
            level: Priority level (lower numbers = higher priority)
        """
        self.extractors[name] = {
            'extractor': extractor,
            'level': level
        }
        logger.info(f"Registered extractor '{name}' at level {level}")
    
    def process_pdf(self, pdf_path: Path, paper_metadata: Dict) -> Dict[str, Any]:
        """Main processing pipeline using split strategy.
        
        Args:
            pdf_path: Path to the PDF file to process
            paper_metadata: Metadata about the paper (title, authors, etc.)
            
        Returns:
            Dictionary containing extraction results:
                - affiliations: List of extracted affiliations
                - full_text: Full document text  
                - computational_specs: Computational requirements
                - extraction_timestamp: When extraction was performed
                - method: Which extractor was used
        """
        # Step 1: Process first 2 pages for affiliations
        affiliation_data = self._extract_affiliations(pdf_path, paper_metadata)
        
        # Step 2: Extract full text for computational specs
        full_text = self._extract_full_text(pdf_path)
        
        # Step 3: Extract computational requirements
        comp_specs = self._extract_computational_specs(full_text)
        
        return {
            **affiliation_data,
            'full_text': full_text,
            'computational_specs': comp_specs,
            'extraction_timestamp': datetime.now()
        }
    
    def _extract_affiliations(self, pdf_path: Path, metadata: Dict) -> Dict:
        """Try extractors in priority order for first 2 pages.
        
        Args:
            pdf_path: Path to PDF file
            metadata: Paper metadata for validation
            
        Returns:
            Dictionary with affiliations and extraction method
        """
        # Get extractors that can handle affiliations, sorted by priority level
        suitable_extractors = [
            (info['level'], name, info['extractor'])
            for name, info in self.extractors.items()
            if info['extractor'].can_extract_affiliations()
        ]
        
        if not suitable_extractors:
            logger.warning("No extractors capable of affiliation extraction")
            return {'affiliations': [], 'method': 'failed'}
        
        # Sort by level (lower = higher priority)
        suitable_extractors.sort(key=lambda x: x[0])
        
        # Try each extractor in priority order
        for level, name, extractor in suitable_extractors:
            try:
                logger.info(f"Trying extractor '{name}' for affiliations")
                result = extractor.extract_first_pages(pdf_path, pages=[0, 1])
                
                if self.validator.validate_affiliations(result, metadata):
                    logger.info(f"Successfully extracted affiliations using '{name}'")
                    
                    # Record cost for this extraction
                    extraction_cost = self._calculate_extraction_cost(name, 'affiliation_extraction', result)
                    self.cost_tracker.record_extraction_cost(name, 'affiliation_extraction', extraction_cost)
                    
                    return {
                        'affiliations': result.get('affiliations', []),
                        'method': result.get('method', name),
                        'confidence': result.get('confidence', 0.0)
                    }
                else:
                    logger.warning(f"Validation failed for extractor '{name}'")
                    
            except Exception as e:
                logger.error(f"Extractor '{name}' failed: {str(e)}")
                continue
        
        # All extractors failed
        logger.error("All affiliation extractors failed")
        return {'affiliations': [], 'method': 'failed'}
    
    def _extract_full_text(self, pdf_path: Path) -> str:
        """Extract full text using first available extractor.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Full document text or empty string if all fail
        """
        # Get any extractor, sorted by priority
        available_extractors = [
            (info['level'], name, info['extractor'])
            for name, info in self.extractors.items()
        ]
        
        if not available_extractors:
            logger.error("No extractors available for full text extraction")
            return ""
        
        # Sort by level and try each one
        available_extractors.sort(key=lambda x: x[0])
        
        for level, name, extractor in available_extractors:
            try:
                logger.info(f"Extracting full text using '{name}'")
                full_text = extractor.extract_full_text(pdf_path)
                
                # Record cost for full text extraction
                extraction_cost = self._calculate_extraction_cost(name, 'full_text', {'text': full_text})
                self.cost_tracker.record_extraction_cost(name, 'full_text', extraction_cost)
                
                return full_text
            except Exception as e:
                logger.error(f"Full text extraction failed with '{name}': {str(e)}")
                continue
        
        logger.error("All full text extractors failed")
        return ""
    
    def _extract_computational_specs(self, full_text: str) -> Dict:
        """Extract computational specifications from full text.
        
        Args:
            full_text: Full document text
            
        Returns:
            Dictionary with computational requirements
        """
        # Placeholder implementation - in real system would use ComputationalAnalyzer
        if not full_text:
            return {}
        
        # Simple keyword-based detection for now
        computational_keywords = ['GPU', 'CPU', 'memory', 'compute', 'training', 'inference']
        found_keywords = [kw for kw in computational_keywords if kw.lower() in full_text.lower()]
        
        return {
            'found_keywords': found_keywords,
            'has_computational_content': len(found_keywords) > 0
        }
    
    def _calculate_extraction_cost(self, extractor_name: str, operation: str, result: Dict) -> float:
        """Calculate cost for an extraction operation.
        
        Args:
            extractor_name: Name of the extractor used
            operation: Type of operation performed
            result: Result of the extraction
            
        Returns:
            Cost in dollars for this operation
        """
        # Cost mapping for different extractors
        cost_map = {
            'claude_vision': {
                'affiliation_extraction': 0.10,  # Per 2-page extraction
                'full_text': 0.15  # Per full document
            },
            'google_vision': {
                'affiliation_extraction': 0.05,  # Per 2-page extraction
                'full_text': 0.08,  # Per full document
                'ocr': 0.03  # Per page
            },
            'pymupdf': {
                'affiliation_extraction': 0.0,  # Free
                'full_text': 0.0  # Free
            },
            'easyocr': {
                'affiliation_extraction': 0.0,  # Free but uses local compute
                'full_text': 0.0,
                'ocr': 0.0
            },
            'grobid': {
                'affiliation_extraction': 0.0,  # Free
                'full_text': 0.0
            }
        }
        
        return cost_map.get(extractor_name, {}).get(operation, 0.0)
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get summary of extraction costs.
        
        Returns:
            Dictionary with cost breakdown
        """
        return self.cost_tracker.get_cost_summary()