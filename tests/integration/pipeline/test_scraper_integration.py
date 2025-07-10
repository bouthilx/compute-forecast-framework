"""Integration test demonstrating scraper models usage"""

from unittest.mock import Mock

from compute_forecast.data.sources.scrapers import (
    SimplePaper,
    PaperoniAdapter,
    ScrapingBatch,
)
from compute_forecast.data.models import Paper, Author


def test_simple_paper_to_package_integration():
    """Test complete flow from SimplePaper to package Paper"""
    # Create a SimplePaper from scraping
    scraped_paper = SimplePaper(
        title="Deep Learning for Computer Vision",
        authors=["Jane Doe", "John Smith"],
        venue="CVPR",
        year=2024,
        abstract="This paper presents a novel deep learning approach...",
        pdf_url="https://example.com/paper.pdf",
        doi="10.1234/cvpr.2024.12345",
        source_scraper="cvpr_scraper",
        extraction_confidence=0.9,
    )

    # Convert to package format
    package_paper = scraped_paper.to_package_paper()

    # Verify it's a valid Paper object
    assert isinstance(package_paper, Paper)
    assert package_paper.title == "Deep Learning for Computer Vision"
    assert len(package_paper.authors) == 2
    assert all(isinstance(author, Author) for author in package_paper.authors)
    assert package_paper.venue == "CVPR"
    assert package_paper.year == 2024
    assert package_paper.citations == 0  # Default for scraped papers
    assert package_paper.collection_source == "cvpr_scraper"


def test_paperoni_adapter_integration():
    """Test paperoni adapter in realistic scenario"""
    # Mock a paperoni paper object with realistic structure
    mock_author1 = Mock()
    mock_author1.name = "Alice Johnson"
    mock_paper_author1 = Mock()
    mock_paper_author1.author = mock_author1

    mock_author2 = Mock()
    mock_author2.name = "Bob Williams"
    mock_paper_author2 = Mock()
    mock_paper_author2.author = mock_author2

    mock_venue = Mock()
    mock_venue.name = "NeurIPS"

    mock_date = Mock()
    mock_date.year = 2023

    mock_release = Mock()
    mock_release.venue = mock_venue
    mock_release.date = mock_date

    mock_link = Mock()
    mock_link.type = "pdf"
    mock_link.url = "https://papers.nips.cc/paper/2023/file/abc123.pdf"

    mock_paperoni_paper = Mock()
    mock_paperoni_paper.title = "Transformers for Sequential Decision Making"
    mock_paperoni_paper.authors = [mock_paper_author1, mock_paper_author2]
    mock_paperoni_paper.releases = [mock_release]
    mock_paperoni_paper.links = [mock_link]
    mock_paperoni_paper.abstract = "We propose a transformer-based approach..."
    mock_paperoni_paper.doi = "10.5555/neurips.2023.9876"

    # Use adapter to convert
    adapter = PaperoniAdapter()
    simple_paper = adapter.convert(mock_paperoni_paper)

    # Verify conversion
    assert simple_paper.title == "Transformers for Sequential Decision Making"
    assert simple_paper.authors == ["Alice Johnson", "Bob Williams"]
    assert simple_paper.venue == "NeurIPS"
    assert simple_paper.year == 2023
    assert simple_paper.pdf_url == "https://papers.nips.cc/paper/2023/file/abc123.pdf"
    assert simple_paper.source_scraper == "paperoni"

    # Convert to package format
    package_paper = simple_paper.to_package_paper()
    assert isinstance(package_paper, Paper)
    assert package_paper.collection_source == "paperoni"


def test_scraping_batch_workflow():
    """Test complete scraping batch workflow"""
    # Simulate scraping multiple papers
    papers = []
    errors = []

    # Successfully scraped papers
    for i in range(1, 8):
        paper = SimplePaper(
            title=f"Research Paper {i}",
            authors=[f"Author {i}"],
            venue="ICML",
            year=2024,
            pdf_url=f"https://icml.cc/paper{i}.pdf",
            source_scraper="icml_scraper",
        )
        papers.append(paper)

    # Track errors for failed papers
    errors.extend(
        [
            "Failed to parse paper 8: Malformed HTML",
            "Failed to parse paper 9: Connection timeout",
            "Failed to parse paper 10: Access denied",
        ]
    )

    # Create batch result
    batch = ScrapingBatch(
        papers=papers,
        source="icml_scraper",
        venue="ICML",
        year=2024,
        total_found=10,
        successfully_parsed=7,
        errors=errors,
    )

    # Verify batch statistics
    assert len(batch.papers) == 7
    assert batch.success_rate == 0.7
    assert len(batch.errors) == 3

    # Convert all papers to package format
    package_papers = [p.to_package_paper() for p in batch.papers]
    assert all(isinstance(p, Paper) for p in package_papers)
    assert all(p.venue == "ICML" for p in package_papers)
    assert all(p.collection_source == "icml_scraper" for p in package_papers)
