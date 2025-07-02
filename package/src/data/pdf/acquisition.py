"""PDF acquisition manager for comprehensive paper PDF retrieval."""

import json
import requests
import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus, urlparse
import hashlib
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PDFSearchResult:
    """Result of PDF search attempt."""
    paper_id: str
    title: str
    pdf_found: bool
    pdf_url: Optional[str]
    pdf_path: Optional[Path]
    source: Optional[str]
    sources_tried: List[str]
    error_messages: List[str]
    search_time: float


class PDFAcquisitionManager:
    """Orchestrates PDF acquisition from multiple sources."""
    
    def __init__(self, cache_dir: Path = Path("data/pdf_cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all PDF sources
        self.sources = [
            SemanticScholarPDFSource(),
            ArXivPDFSource(),
            UnpaywallPDFSource(),
            GoogleScholarPDFSource(),
            RepositoryPDFSource(),
            ConferencePDFSource(),
        ]
        
        # Rate limiting
        self.last_request_time = {}
        self.min_delay = 2.0  # seconds between requests per domain
        
    def acquire_pdf(self, paper: Dict[str, Any]) -> PDFSearchResult:
        """Acquire PDF for a paper using all available sources."""
        start_time = time.time()
        
        paper_id = paper.get('paper_id', paper.get('id', self._generate_paper_id(paper)))
        title = paper.get('title', 'Unknown')
        
        result = PDFSearchResult(
            paper_id=paper_id,
            title=title,
            pdf_found=False,
            pdf_url=None,
            pdf_path=None,
            source=None,
            sources_tried=[],
            error_messages=[],
            search_time=0
        )
        
        # Check cache first
        cached_path = self._check_cache(paper_id)
        if cached_path and cached_path.exists():
            logger.info(f"PDF found in cache: {cached_path}")
            result.pdf_found = True
            result.pdf_path = cached_path
            result.source = "cache"
            result.search_time = time.time() - start_time
            return result
        
        # Try each source
        for source in self.sources:
            source_name = source.__class__.__name__
            logger.info(f"Trying {source_name} for: {title[:60]}...")
            
            try:
                result.sources_tried.append(source_name)
                pdf_url = source.find_pdf(paper)
                
                if pdf_url:
                    logger.info(f"PDF URL found via {source_name}: {pdf_url}")
                    
                    # Download and verify PDF
                    pdf_path = self._download_pdf(pdf_url, paper_id)
                    if pdf_path and self._verify_pdf(pdf_path):
                        result.pdf_found = True
                        result.pdf_url = pdf_url
                        result.pdf_path = pdf_path
                        result.source = source_name
                        result.search_time = time.time() - start_time
                        return result
                    else:
                        result.error_messages.append(f"{source_name}: Download/verification failed")
                        
            except Exception as e:
                error_msg = f"{source_name} error: {str(e)}"
                logger.error(error_msg)
                result.error_messages.append(error_msg)
        
        result.search_time = time.time() - start_time
        return result
    
    def _generate_paper_id(self, paper: Dict[str, Any]) -> str:
        """Generate unique ID for paper."""
        title = paper.get('title', '')
        year = paper.get('year', '')
        authors = paper.get('authors', [])
        
        first_author = ''
        if authors and len(authors) > 0:
            if isinstance(authors[0], dict):
                first_author = authors[0].get('name', '')
            elif isinstance(authors[0], str):
                first_author = authors[0]
        
        id_string = f"{title}_{year}_{first_author}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def _check_cache(self, paper_id: str) -> Optional[Path]:
        """Check if PDF exists in cache."""
        pdf_path = self.cache_dir / f"{paper_id}.pdf"
        return pdf_path if pdf_path.exists() else None
    
    def _download_pdf(self, pdf_url: str, paper_id: str) -> Optional[Path]:
        """Download PDF with rate limiting and verification."""
        try:
            # Rate limit by domain
            domain = urlparse(pdf_url).netloc
            self._rate_limit(domain)
            
            # Download
            headers = {
                'User-Agent': 'Mozilla/5.0 (scholarly-pdf-fetcher/1.0)'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                pdf_path = self.cache_dir / f"{paper_id}.pdf"
                
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                return pdf_path
            else:
                logger.error(f"Download failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    def _verify_pdf(self, pdf_path: Path) -> bool:
        """Verify PDF is valid."""
        try:
            # Check file size
            if pdf_path.stat().st_size < 1000:  # Less than 1KB
                return False
            
            # Check PDF header
            with open(pdf_path, 'rb') as f:
                header = f.read(5)
                return header == b'%PDF-'
                
        except Exception:
            return False
    
    def _rate_limit(self, domain: str):
        """Enforce rate limiting per domain."""
        current_time = time.time()
        
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                logger.debug(f"Rate limiting {domain}: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()


class SemanticScholarPDFSource:
    """Semantic Scholar PDF source using their API."""
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Find PDF using Semantic Scholar API."""
        # Extract paper ID
        paper_id = None
        
        # From URL
        if paper.get('url'):
            match = re.search(r'semanticscholar\.org/paper/([a-f0-9]+)', paper['url'])
            if match:
                paper_id = match.group(1)
        
        # From ID field
        if not paper_id and paper.get('id'):
            paper_id = paper['id']
        
        if not paper_id:
            return None
        
        # Call S2 API with openAccessPdf field
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
        params = {
            'fields': 'openAccessPdf,isOpenAccess,externalIds'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check for open access PDF
                if data.get('openAccessPdf'):
                    pdf_info = data['openAccessPdf']
                    return pdf_info.get('url')
                
                # Check for ArXiv ID as fallback
                external_ids = data.get('externalIds', {})
                if external_ids.get('ArXiv'):
                    arxiv_id = external_ids['ArXiv']
                    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    
        except Exception as e:
            logger.error(f"S2 API error: {e}")
        
        return None


class ArXivPDFSource:
    """ArXiv PDF source with multiple search strategies."""
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Find PDF on ArXiv using multiple strategies."""
        strategies = [
            self._search_by_exact_title,
            self._search_by_title_keywords,
            self._search_by_author_and_year,
            self._search_by_abstract_similarity,
        ]
        
        for strategy in strategies:
            try:
                pdf_url = strategy(paper)
                if pdf_url:
                    return pdf_url
            except Exception as e:
                logger.debug(f"ArXiv strategy {strategy.__name__} failed: {e}")
        
        return None
    
    def _search_by_exact_title(self, paper: Dict[str, Any]) -> Optional[str]:
        """Search ArXiv by exact title match."""
        title = paper.get('title', '')
        if not title:
            return None
        
        # Clean title
        title_clean = re.sub(r'[^\w\s]', ' ', title)
        title_clean = ' '.join(title_clean.split())
        
        query = f'ti:"{title_clean}"'
        return self._search_arxiv_api(query, paper)
    
    def _search_by_title_keywords(self, paper: Dict[str, Any]) -> Optional[str]:
        """Search by key title words."""
        title = paper.get('title', '')
        if not title:
            return None
        
        # Extract significant words
        keywords = self._extract_keywords(title)
        if len(keywords) < 3:
            return None
        
        query = f'all:{" ".join(keywords[:5])}'
        return self._search_arxiv_api(query, paper)
    
    def _search_by_author_and_year(self, paper: Dict[str, Any]) -> Optional[str]:
        """Search by first author and year."""
        authors = paper.get('authors', [])
        year = paper.get('year')
        title_keywords = self._extract_keywords(paper.get('title', ''))
        
        if not authors or not year or not title_keywords:
            return None
        
        first_author = authors[0].get('name', '').split()[-1]  # Last name
        query = f'au:{first_author} AND all:{year} AND all:{" ".join(title_keywords[:2])}'
        
        return self._search_arxiv_api(query, paper)
    
    def _search_by_abstract_similarity(self, paper: Dict[str, Any]) -> Optional[str]:
        """Search using abstract text if available."""
        abstract = paper.get('abstract', '')
        if not abstract or len(abstract) < 100:
            return None
        
        # Extract key phrases from abstract
        key_phrases = self._extract_key_phrases(abstract)
        if not key_phrases:
            return None
        
        query = f'abs:{" ".join(key_phrases[:3])}'
        return self._search_arxiv_api(query, paper)
    
    def _search_arxiv_api(self, query: str, paper: Dict[str, Any]) -> Optional[str]:
        """Execute ArXiv API search."""
        url = f"http://export.arxiv.org/api/query"
        params = {
            'search_query': query,
            'start': 0,
            'max_results': 10
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                # Parse results
                entries = self._parse_arxiv_response(response.text)
                
                # Find best match
                for entry in entries:
                    if self._is_same_paper(entry, paper):
                        return entry.get('pdf_url')
                        
        except Exception as e:
            logger.error(f"ArXiv API error: {e}")
        
        return None
    
    def _parse_arxiv_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse ArXiv API XML response."""
        entries = []
        
        # Simple XML parsing
        entry_pattern = r'<entry>(.*?)</entry>'
        for match in re.finditer(entry_pattern, xml_text, re.DOTALL):
            entry_text = match.group(1)
            
            entry = {}
            
            # Extract title
            title_match = re.search(r'<title>(.*?)</title>', entry_text)
            if title_match:
                entry['title'] = title_match.group(1).strip()
            
            # Extract PDF URL
            pdf_match = re.search(r'<link.*?title="pdf".*?href="([^"]+)"', entry_text)
            if pdf_match:
                entry['pdf_url'] = pdf_match.group(1)
            
            # Extract authors
            authors = []
            for author_match in re.finditer(r'<author>.*?<name>(.*?)</name>', entry_text, re.DOTALL):
                authors.append(author_match.group(1).strip())
            entry['authors'] = authors
            
            # Extract year from published date
            date_match = re.search(r'<published>(\d{4})', entry_text)
            if date_match:
                entry['year'] = int(date_match.group(1))
            
            if entry.get('title') and entry.get('pdf_url'):
                entries.append(entry)
        
        return entries
    
    def _is_same_paper(self, arxiv_entry: Dict[str, Any], paper: Dict[str, Any]) -> bool:
        """Check if ArXiv entry matches the paper."""
        # Title similarity
        title_sim = self._title_similarity(
            arxiv_entry.get('title', ''),
            paper.get('title', '')
        )
        
        if title_sim > 0.85:
            return True
        
        # Author overlap + year match
        if arxiv_entry.get('year') == paper.get('year'):
            arxiv_authors = set(a.split()[-1].lower() for a in arxiv_entry.get('authors', []))
            paper_authors = set(a['name'].split()[-1].lower() for a in paper.get('authors', [])[:3])
            
            if arxiv_authors and paper_authors:
                overlap = len(arxiv_authors.intersection(paper_authors))
                if overlap >= 1 and title_sim > 0.6:
                    return True
        
        return False
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity score."""
        # Normalize
        t1 = re.sub(r'[^\w\s]', ' ', title1.lower())
        t2 = re.sub(r'[^\w\s]', ' ', title2.lower())
        
        t1_words = set(t1.split())
        t2_words = set(t2.split())
        
        if not t1_words or not t2_words:
            return 0.0
        
        intersection = len(t1_words.intersection(t2_words))
        union = len(t1_words.union(t2_words))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract significant keywords from text."""
        # Remove common words
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were',
            'using', 'based', 'via'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = []
        
        for word in words:
            if (len(word) > 2 and word not in stopwords) or word.isupper():
                keywords.append(word)
        
        return keywords
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text."""
        # Look for technical terms and acronyms
        phrases = []
        
        # Find capitalized sequences
        cap_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        phrases.extend(re.findall(cap_pattern, text))
        
        # Find acronyms
        acronym_pattern = r'\b[A-Z]{2,}\b'
        phrases.extend(re.findall(acronym_pattern, text))
        
        return phrases[:5]  # Top 5 phrases


class UnpaywallPDFSource:
    """Unpaywall open access PDF source."""
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Find PDF via Unpaywall using DOI."""
        doi = self._extract_doi(paper)
        if not doi:
            return None
        
        # Unpaywall API
        email = "research@example.com"  # Should be configured
        url = f"https://api.unpaywall.org/v2/{doi}"
        params = {'email': email}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('is_oa'):
                    # Get best OA location
                    best_oa = data.get('best_oa_location')
                    if best_oa:
                        return best_oa.get('url_for_pdf') or best_oa.get('url')
                        
        except Exception as e:
            logger.error(f"Unpaywall error: {e}")
        
        return None
    
    def _extract_doi(self, paper: Dict[str, Any]) -> Optional[str]:
        """Extract DOI from paper."""
        # Direct DOI field
        if paper.get('doi'):
            return paper['doi']
        
        # From abstract or other text
        doi_pattern = r'10\.\d{4,}/[-._;()/:\w]+'
        
        for field in ['abstract', 'title']:
            text = paper.get(field, '')
            if text:
                match = re.search(doi_pattern, text)
                if match:
                    return match.group()
        
        return None


class GoogleScholarPDFSource:
    """Google Scholar PDF source (placeholder for full implementation)."""
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Find PDF via Google Scholar."""
        # Would implement actual Google Scholar search
        # Using scholarly library or web scraping
        # For now, return None to avoid complexity
        return None


class RepositoryPDFSource:
    """Institutional repository PDF source."""
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Search institutional repositories."""
        # Would search:
        # - CORE (core.ac.uk)
        # - BASE (base-search.net)
        # - PubMed Central
        # - University repositories
        return None


class ConferencePDFSource:
    """Conference proceedings PDF source."""
    
    def find_pdf(self, paper: Dict[str, Any]) -> Optional[str]:
        """Search conference proceedings sites."""
        venue = paper.get('venue', '').lower()
        year = paper.get('year')
        
        if not venue:
            return None
        
        # Conference sites with open proceedings
        if 'neurips' in venue or 'nips' in venue:
            # papers.nips.cc
            return None
        elif any(v in venue for v in ['cvpr', 'iccv', 'eccv']):
            # openaccess.thecvf.com
            return None
        elif 'icml' in venue:
            # proceedings.mlr.press
            return None
        elif 'iclr' in venue:
            # openreview.net
            return None
        elif any(v in venue for v in ['acl', 'emnlp', 'naacl']):
            # aclanthology.org
            return None
        
        return None