"""GROBID-based academic structure extractor."""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any

import requests
from pypdf import PdfReader, PdfWriter
from lxml import etree

from src.pdf_parser.core.base_extractor import BaseExtractor
from src.pdf_parser.services.grobid_manager import GROBIDManager, GROBIDServiceError

logger = logging.getLogger(__name__)


class GROBIDExtractionError(Exception):
    """Exception raised for GROBID extraction errors."""
    pass


class GROBIDExtractor(BaseExtractor):
    """GROBID-based extractor for academic paper structure and affiliations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize GROBID extractor.
        
        Args:
            config: Configuration dictionary with optional keys:
                - grobid_url: GROBID service URL (default: http://localhost:8070)
                - timeout: Request timeout (default: 30)
        """
        config = config or {}
        
        self.grobid_url = config.get('grobid_url', 'http://localhost:8070')
        self.timeout = config.get('timeout', 30)
        
        # Initialize GROBID service manager
        manager_config = {
            'url': self.grobid_url,
            'timeout': self.timeout
        }
        self.manager = GROBIDManager(manager_config)
        
        logger.info(f"Initialized GROBID extractor for {self.grobid_url}")
    
    def can_extract_affiliations(self) -> bool:
        """Check if this extractor can be used for affiliation extraction.
        
        Returns:
            True - GROBID is excellent for affiliation extraction
        """
        return True
    
    def extract_first_pages(self, pdf_path: Path, pages: List[int]) -> Dict:
        """Extract structured data from specific pages using GROBID.
        
        Args:
            pdf_path: Path to the PDF file
            pages: List of page indices to extract (0-based)
            
        Returns:
            Dictionary containing:
                - affiliations: List of extracted affiliations
                - authors_with_affiliations: List of authors with their affiliations
                - title: Paper title
                - abstract: Paper abstract
                - method: 'grobid'
                - confidence: 0.8 (GROBID is generally reliable)
        """
        if not pdf_path.exists():
            raise GROBIDExtractionError(f"PDF file not found: {pdf_path}")
        
        try:
            # Ensure GROBID service is running
            self.manager.ensure_service_running()
        except GROBIDServiceError as e:
            raise GROBIDExtractionError(f"GROBID service unavailable: {str(e)}")
        
        # Create temporary PDF with just the specified pages
        temp_pdf_path = self._extract_pages_to_pdf(pdf_path, pages)
        
        try:
            # Send to GROBID header extraction endpoint
            with open(temp_pdf_path, 'rb') as f:
                response = requests.post(
                    f'{self.grobid_url}/api/processHeaderDocument',
                    files={'input': f},
                    timeout=self.timeout
                )
            
            if response.status_code != 200:
                raise GROBIDExtractionError(
                    f"GROBID API request failed with status {response.status_code}: {response.text}"
                )
            
            # Parse TEI XML response
            parsed_data = self._parse_grobid_xml(response.text)
            
            return {
                'affiliations': parsed_data.get('affiliations', []),
                'authors_with_affiliations': parsed_data.get('authors', []),
                'title': parsed_data.get('title', ''),
                'abstract': parsed_data.get('abstract', ''),
                'method': 'grobid',
                'confidence': 0.8  # GROBID is generally reliable for academic papers
            }
            
        except requests.RequestException as e:
            raise GROBIDExtractionError(f"GROBID API request failed: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                temp_pdf_path.unlink()
            except FileNotFoundError:
                pass  # File was already deleted or didn't exist
    
    def extract_full_text(self, pdf_path: Path) -> str:
        """Extract full text from PDF using GROBID.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Full text content of the document
        """
        if not pdf_path.exists():
            raise GROBIDExtractionError(f"PDF file not found: {pdf_path}")
        
        try:
            # Ensure GROBID service is running
            self.manager.ensure_service_running()
        except GROBIDServiceError as e:
            raise GROBIDExtractionError(f"GROBID service unavailable: {str(e)}")
        
        try:
            # Send to GROBID full text extraction endpoint
            with open(pdf_path, 'rb') as f:
                response = requests.post(
                    f'{self.grobid_url}/api/processFulltextDocument',
                    files={'input': f},
                    timeout=self.timeout
                )
            
            if response.status_code != 200:
                raise GROBIDExtractionError(
                    f"GROBID full text API request failed with status {response.status_code}: {response.text}"
                )
            
            return response.text
            
        except requests.RequestException as e:
            raise GROBIDExtractionError(f"GROBID full text API request failed: {str(e)}")
    
    def _extract_pages_to_pdf(self, pdf_path: Path, pages: List[int]) -> Path:
        """Extract specific pages to a temporary PDF file.
        
        Args:
            pdf_path: Source PDF path
            pages: List of 0-based page indices to extract
            
        Returns:
            Path to temporary PDF file with extracted pages
        """
        try:
            # Read source PDF
            with open(pdf_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                pdf_writer = PdfWriter()
                
                # Add specified pages to writer
                for page_idx in pages:
                    if page_idx < len(pdf_reader.pages):
                        pdf_writer.add_page(pdf_reader.pages[page_idx])
                    else:
                        logger.warning(f"Page {page_idx} not found in PDF with {len(pdf_reader.pages)} pages")
                
                # Write to temporary file
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_path = Path(temp_file.name)
                
                with open(temp_path, 'wb') as temp_pdf:
                    pdf_writer.write(temp_pdf)
                
                return temp_path
                
        except Exception as e:
            raise GROBIDExtractionError(f"Failed to extract pages from PDF: {str(e)}")
    
    def _parse_grobid_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse GROBID TEI XML to extract structured data.
        
        Args:
            xml_content: TEI XML string from GROBID
            
        Returns:
            Dictionary with parsed author, affiliation, title, and abstract data
        """
        try:
            # Parse XML with TEI namespace
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Extract title
            title_elements = root.xpath('//tei:title[@type="main"]//text()', namespaces=ns)
            title = ' '.join(title_elements).strip()
            
            # Extract abstract
            abstract_elements = root.xpath('//tei:abstract//text()', namespaces=ns)
            abstract = ' '.join(abstract_elements).strip()
            
            # Extract authors with affiliations
            authors = []
            author_elements = root.xpath('//tei:author', namespaces=ns)
            
            for author_elem in author_elements:
                # Get author name
                name_parts = author_elem.xpath('.//tei:persName//text()', namespaces=ns)
                name = ' '.join(name_parts).strip()
                
                if not name:
                    continue  # Skip if no name found
                
                # Get affiliations for this author
                affiliations = []
                aff_elements = author_elem.xpath('.//tei:affiliation', namespaces=ns)
                
                for aff_elem in aff_elements:
                    # Extract organization name
                    org_elements = aff_elem.xpath('.//tei:orgName//text()', namespaces=ns)
                    org_name = ' '.join(org_elements).strip()
                    
                    # Extract address
                    addr_elements = aff_elem.xpath('.//tei:address//text()', namespaces=ns)
                    address = ' '.join(addr_elements).strip()
                    
                    # Combine organization and address
                    affiliation_text = f'{org_name} {address}'.strip()
                    if affiliation_text:
                        affiliations.append(affiliation_text)
                
                authors.append({
                    'name': name,
                    'affiliations': affiliations
                })
            
            # Create unique list of all affiliations
            all_affiliations = []
            for author in authors:
                all_affiliations.extend(author['affiliations'])
            unique_affiliations = list(set(all_affiliations))
            
            return {
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'affiliations': unique_affiliations
            }
            
        except etree.XMLSyntaxError as e:
            raise GROBIDExtractionError(f"Failed to parse XML response from GROBID: {str(e)}")
        except Exception as e:
            raise GROBIDExtractionError(f"Error processing GROBID XML: {str(e)}")