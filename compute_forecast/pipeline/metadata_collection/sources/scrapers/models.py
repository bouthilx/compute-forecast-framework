"""Adapter models to bridge scrapers and package data structures"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from compute_forecast.pipeline.metadata_collection.models import Paper, Author
from compute_forecast.pipeline.consolidation.models import (
    CitationRecord,
    CitationData,
    AbstractRecord,
    AbstractData,
    URLRecord,
    URLData,
)


@dataclass
class SimplePaper:
    """Minimal paper representation from any scraper"""

    # Core fields
    title: str
    authors: List[str]  # Simple list of author names
    venue: str
    year: int

    # Paper identifier
    paper_id: Optional[str] = None

    # Optional fields
    abstract: Optional[str] = None
    pdf_urls: List[str] = field(default_factory=list)  # Multiple PDF URLs
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    keywords: List[str] = field(default_factory=list)  # Extracted keywords

    # Source tracking
    source_scraper: str = ""
    source_url: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)

    # Paper acceptance decision
    decision: Optional[str] = None  # 'oral', 'poster', 'spotlight', or None

    # Quality indicators
    extraction_confidence: float = 1.0

    metadata_completeness: float = 0.0

    def to_package_paper(self) -> Paper:
        """Convert to package's Paper model"""
        # Create provenance records for scraped data
        citations = []
        if hasattr(self, "citations") and self.citations is not None:
            citations.append(
                CitationRecord(
                    source=self.source_scraper,
                    timestamp=self.scraped_at,
                    original=True,  # This is from original scraper
                    data=CitationData(count=self.citations),
                )
            )

        abstracts = []
        if self.abstract:
            abstracts.append(
                AbstractRecord(
                    source=self.source_scraper,
                    timestamp=self.scraped_at,
                    original=True,  # This is from original scraper
                    data=AbstractData(text=self.abstract, language="en"),
                )
            )

        urls = []
        for url in self.pdf_urls:
            urls.append(
                URLRecord(
                    source=self.source_scraper,
                    timestamp=self.scraped_at,
                    original=True,  # This is from original scraper
                    data=URLData(url=url),
                )
            )

        return Paper(
            title=self.title,
            authors=[Author(name=name, affiliations=[]) for name in self.authors],
            venue=self.venue,
            year=self.year,
            citations=citations,
            abstracts=abstracts,
            doi=self.doi or "",
            urls=urls,
            keywords=self.keywords,  # Pass through keywords
            paper_id=self.paper_id,
            arxiv_id=self.arxiv_id,
            collection_source=self.source_scraper,
            collection_timestamp=self.scraped_at,
        )


class PaperoniAdapter:
    """Adapter to convert paperoni models to SimplePaper"""

    @staticmethod
    def convert(paperoni_paper) -> SimplePaper:
        """Convert a paperoni Paper object to SimplePaper"""
        # Extract basic fields
        title = paperoni_paper.title

        # Extract authors (paperoni has complex PaperAuthor → Author structure)
        authors = []
        for paper_author in paperoni_paper.authors:
            if hasattr(paper_author, "author") and hasattr(paper_author.author, "name"):
                authors.append(paper_author.author.name)

        # Extract venue and year from releases
        venue = ""
        year = None
        if paperoni_paper.releases:
            release = paperoni_paper.releases[0]
            if hasattr(release, "venue") and hasattr(release.venue, "name"):
                venue = release.venue.name
            if hasattr(release, "date"):
                year = release.date.year
        # Extract PDF URLs from links
        pdf_urls = []
        for link in paperoni_paper.links:
            if hasattr(link, "type") and "pdf" in str(link.type).lower():
                pdf_urls.append(link.url)

        # Safe extraction of DOI - only if attribute exists and is not a Mock
        doi = None
        if hasattr(paperoni_paper, "doi"):
            doi_value = paperoni_paper.doi
            # Check if it's a real value (not Mock or similar)
            if doi_value and not hasattr(doi_value, "_mock_name"):
                doi = doi_value

        return SimplePaper(
            title=title,
            authors=authors,
            venue=venue,
            year=year or datetime.now().year,
            abstract=paperoni_paper.abstract,
            pdf_urls=pdf_urls,
            doi=doi,
            source_scraper="paperoni",
            extraction_confidence=0.95,  # High confidence for established scrapers
        )


@dataclass
class ScrapingBatch:
    """Container for a batch of scraped papers"""

    papers: List[SimplePaper]
    source: str
    venue: str
    year: int
    total_found: int
    successfully_parsed: int
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate of parsing"""
        return self.successfully_parsed / max(1, self.total_found)
