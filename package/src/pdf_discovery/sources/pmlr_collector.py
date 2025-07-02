"""PMLR (Proceedings of Machine Learning Research) PDF collector."""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

import requests
from rapidfuzz import fuzz
from rapidfuzz import process

from src.pdf_discovery.core.collectors import BasePDFCollector
from src.pdf_discovery.core.models import PDFRecord
from src.data.models import Paper

logger = logging.getLogger(__name__)


class PMLRCollector(BasePDFCollector):
    """Collector for PMLR proceedings papers."""
    
    def __init__(self):
        """Initialize PMLR collector."""
        super().__init__("pmlr")
        self.venue_volumes = {}
        self.base_url = ""
        self.pdf_pattern = ""
        self.proceedings_pattern = ""
        self.aliases = {}
        
        # Load volume mappings
        self._load_volume_mapping()
        
        # Cache for proceedings pages
        self._proceedings_cache = {}
        
        # Configure timeout for HTTP requests
        self.request_timeout = 30
    
    def _load_volume_mapping(self):
        """Load volume mapping from JSON file."""
        data_dir = Path(__file__).parent / "data"
        volumes_file = data_dir / "pmlr_volumes.json"
        
        if not volumes_file.exists():
            raise FileNotFoundError(f"PMLR volumes file not found: {volumes_file}")
        
        with open(volumes_file, 'r') as f:
            data = json.load(f)
        
        self.venue_volumes = data.get("venue_volumes", {})
        self.base_url = data.get("base_url", "https://proceedings.mlr.press/")
        self.pdf_pattern = data.get("pdf_pattern", "v{volume}/{paper_id}.pdf")
        self.proceedings_pattern = data.get("proceedings_pattern", "v{volume}/")
        self.aliases = data.get("aliases", {})
        
        logger.info(f"Loaded PMLR volume mappings for {len(self.venue_volumes)} venues")
    
    def _normalize_venue(self, venue_name: str) -> str:
        """Normalize venue name to standard abbreviation.
        
        Args:
            venue_name: Original venue name
            
        Returns:
            Normalized venue abbreviation
        """
        # Check if it's already a known abbreviation
        if venue_name in self.venue_volumes:
            return venue_name
        
        # Check aliases
        if venue_name in self.aliases:
            return self.aliases[venue_name]
        
        # Try case-insensitive match
        venue_upper = venue_name.upper()
        for abbr in self.venue_volumes:
            if venue_upper == abbr.upper():
                return abbr
        
        # Return original if no match found
        return venue_name
    
    def _get_volume(self, venue: str, year: int) -> Optional[str]:
        """Get volume number for venue and year.
        
        Args:
            venue: Venue abbreviation
            year: Publication year
            
        Returns:
            Volume string (e.g., "v202") or None if not found
        """
        normalized_venue = self._normalize_venue(venue)
        
        if normalized_venue not in self.venue_volumes:
            return None
        
        year_str = str(year)
        return self.venue_volumes[normalized_venue].get(year_str)
    
    def _search_proceedings_page(self, volume: str, paper_title: str) -> Optional[str]:
        """Search proceedings page for paper ID by title.
        
        Args:
            volume: Volume string (e.g., "v202")
            paper_title: Paper title to search for
            
        Returns:
            Paper ID (e.g., "doe23a") or None if not found
        """
        # Check cache first
        cache_key = f"{volume}:{paper_title}"
        if cache_key in self._proceedings_cache:
            return self._proceedings_cache[cache_key]
        
        try:
            # Fetch proceedings page
            proceedings_url = self.base_url + self.proceedings_pattern.format(volume=volume)
            
            response = requests.get(proceedings_url, timeout=self.request_timeout)
            response.raise_for_status()
            
            # Parse paper links
            # Pattern: <a href="/v202/doe23a.html">Paper Title</a>
            pattern = r'<a href="/' + volume + r'/([^"]+)\.html">([^<]+)</a>'
            matches = re.findall(pattern, response.text)
            
            if not matches:
                logger.warning(f"No papers found in proceedings {volume}")
                return None
            
            # Extract titles and IDs
            papers_data = [(paper_id, title.strip()) for paper_id, title in matches]
            titles = [title for _, title in papers_data]
            
            # Use fuzzy matching to find best match
            best_match = process.extractOne(
                paper_title,
                titles,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=85  # Minimum similarity threshold
            )
            
            if best_match:
                matched_title, score, idx = best_match
                paper_id = papers_data[idx][0]
                logger.info(f"Found paper '{paper_title}' as '{matched_title}' (score: {score}) -> {paper_id}")
                
                # Cache the result
                self._proceedings_cache[cache_key] = paper_id
                return paper_id
            
            logger.warning(f"No match found for '{paper_title}' in {volume}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching proceedings {volume}: {e}")
            return None
    
    def _construct_pdf_url(self, volume: str, paper_id: str) -> str:
        """Construct PDF URL from volume and paper ID.
        
        Args:
            volume: Volume string (e.g., "v202")
            paper_id: Paper ID (e.g., "doe23a")
            
        Returns:
            Full PDF URL
        """
        pdf_path = self.pdf_pattern.format(volume=volume, paper_id=paper_id)
        return self.base_url + pdf_path
    
    def _discover_single(self, paper: Paper) -> PDFRecord:
        """Discover PDF for a single paper.
        
        Args:
            paper: Paper to find PDF for
            
        Returns:
            PDFRecord with discovered PDF information
            
        Raises:
            ValueError: If PDF cannot be discovered
        """
        # Get volume for venue and year
        volume = self._get_volume(paper.venue, paper.year)
        if not volume:
            raise ValueError(f"No volume mapping found for {paper.venue} {paper.year}")
        
        # Search proceedings page for paper ID
        paper_id = self._search_proceedings_page(volume, paper.title)
        if not paper_id:
            raise ValueError(f"Paper not found in proceedings: {paper.title}")
        
        # Construct PDF URL
        pdf_url = self._construct_pdf_url(volume, paper_id)
        
        # Create PDF record
        return PDFRecord(
            paper_id=paper.paper_id,
            pdf_url=pdf_url,
            source=self.source_name,
            discovery_timestamp=datetime.now(),
            confidence_score=0.95,  # High confidence for direct venue links
            version_info={
                "volume": volume,
                "paper_id": paper_id,
                "venue": paper.venue,
                "year": paper.year
            },
            validation_status="verified"
        )