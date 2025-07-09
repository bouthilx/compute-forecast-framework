"""Unit tests for scraper models - TDD approach"""

from datetime import datetime
from unittest.mock import Mock

from compute_forecast.data.sources.scrapers.models import (
    SimplePaper,
    PaperoniAdapter,
    ScrapingBatch,
)
from compute_forecast.data.models import Paper, Author


class TestSimplePaper:
    """Test SimplePaper dataclass"""

    def test_simple_paper_creation_with_required_fields(self):
        """Test creating SimplePaper with required fields only"""
        paper = SimplePaper(
            title="Test Paper",
            authors=["Alice Smith", "Bob Jones"],
            venue="NeurIPS",
            year=2024,
        )

        assert paper.title == "Test Paper"
        assert paper.authors == ["Alice Smith", "Bob Jones"]
        assert paper.venue == "NeurIPS"
        assert paper.year == 2024

        # Check defaults
        assert paper.abstract is None
        assert paper.pdf_urls == []
        assert paper.doi is None
        assert paper.source_scraper == ""
        assert paper.source_url == ""
        assert paper.extraction_confidence == 1.0
        assert paper.metadata_completeness == 0.0
        assert paper.paper_id is None
        assert paper.arxiv_id is None
        assert isinstance(paper.scraped_at, datetime)

    def test_simple_paper_creation_with_all_fields(self):
        """Test creating SimplePaper with all fields"""
        scraped_time = datetime(2024, 1, 1, 12, 0, 0)
        paper = SimplePaper(
            title="Advanced ML Paper",
            authors=["Carol Davis"],
            venue="ICML",
            year=2023,
            abstract="This paper presents a novel approach...",
            pdf_urls=["https://example.com/paper.pdf"],
            doi="10.1234/example.doi",
            source_scraper="custom_scraper",
            source_url="https://example.com/proceedings",
            scraped_at=scraped_time,
            extraction_confidence=0.95,
        )

        assert paper.abstract == "This paper presents a novel approach..."
        assert paper.pdf_urls == ["https://example.com/paper.pdf"]
        assert paper.doi == "10.1234/example.doi"
        assert paper.source_scraper == "custom_scraper"
        assert paper.source_url == "https://example.com/proceedings"
        assert paper.scraped_at == scraped_time
        assert paper.extraction_confidence == 0.95

    def test_to_package_paper_conversion(self):
        """Test conversion to package Paper model"""
        simple_paper = SimplePaper(
            title="Conversion Test Paper",
            authors=["Eve Wilson", "Frank Miller"],
            venue="IJCAI",
            year=2024,
            abstract="Test abstract",
            pdf_urls=["https://example.com/test.pdf"],
            doi="10.5678/test",
            source_scraper="test_scraper",
            scraped_at=datetime(2024, 1, 15, 10, 30, 0),
        )

        package_paper = simple_paper.to_package_paper()

        # Verify conversion
        assert isinstance(package_paper, Paper)
        assert package_paper.title == "Conversion Test Paper"
        assert len(package_paper.authors) == 2
        assert isinstance(package_paper.authors[0], Author)
        assert package_paper.authors[0].name == "Eve Wilson"
        assert package_paper.authors[0].affiliation == ""
        assert package_paper.authors[1].name == "Frank Miller"
        assert package_paper.venue == "IJCAI"
        assert package_paper.year == 2024
        assert package_paper.abstract == "Test abstract"
        assert package_paper.doi == "10.5678/test"
        assert package_paper.urls == ["https://example.com/test.pdf"]
        assert package_paper.collection_source == "test_scraper"
        assert package_paper.collection_timestamp == datetime(2024, 1, 15, 10, 30, 0)

    def test_to_package_paper_with_missing_fields(self):
        """Test conversion with None/empty fields"""
        simple_paper = SimplePaper(
            title="Minimal Paper",
            authors=["Single Author"],
            venue="Workshop",
            year=2023,
        )

        package_paper = simple_paper.to_package_paper()

        assert package_paper.abstract == ""
        assert package_paper.doi == ""
        assert package_paper.urls == []
        assert package_paper.collection_source == ""


class TestPaperoniAdapter:
    """Test PaperoniAdapter for converting paperoni models"""

    def create_mock_paperoni_paper(self, **kwargs):
        """Create a mock paperoni paper object"""
        # Create mock author structure
        mock_author = Mock()
        mock_author.name = kwargs.get("author_name", "Test Author")

        mock_paper_author = Mock()
        mock_paper_author.author = mock_author

        # Create mock release/venue structure
        mock_venue = Mock()
        mock_venue.name = kwargs.get("venue_name", "Test Conference")

        mock_date = Mock()
        mock_date.year = kwargs.get("year", 2024)

        mock_release = Mock()
        mock_release.venue = mock_venue
        mock_release.date = mock_date

        # Create mock link structure
        mock_link = Mock()
        mock_link.type = kwargs.get("link_type", "pdf")
        mock_link.url = kwargs.get("pdf_url", "https://example.com/paper.pdf")

        # Create main paper mock
        mock_paper = Mock()
        mock_paper.title = kwargs.get("title", "Test Paper Title")
        mock_paper.authors = kwargs.get("authors", [mock_paper_author])
        mock_paper.releases = kwargs.get("releases", [mock_release])
        mock_paper.links = kwargs.get("links", [mock_link])
        mock_paper.abstract = kwargs.get("abstract", "Test abstract content")
        mock_paper.doi = kwargs.get("doi", "10.1234/test.doi")

        return mock_paper

    def test_paperoni_adapter_basic_conversion(self):
        """Test basic conversion from paperoni paper"""
        mock_paper = self.create_mock_paperoni_paper()

        adapter = PaperoniAdapter()
        simple_paper = adapter.convert(mock_paper)

        assert isinstance(simple_paper, SimplePaper)
        assert simple_paper.title == "Test Paper Title"
        assert simple_paper.authors == ["Test Author"]
        assert simple_paper.venue == "Test Conference"
        assert simple_paper.year == 2024
        assert simple_paper.abstract == "Test abstract content"
        assert simple_paper.pdf_urls == ["https://example.com/paper.pdf"]
        assert simple_paper.doi == "10.1234/test.doi"
        assert simple_paper.source_scraper == "paperoni"
        assert simple_paper.extraction_confidence == 0.95

    def test_paperoni_adapter_multiple_authors(self):
        """Test conversion with multiple authors"""
        # Create multiple mock authors
        authors = []
        for i, name in enumerate(["Alice", "Bob", "Charlie"]):
            mock_author = Mock()
            mock_author.name = name
            mock_paper_author = Mock()
            mock_paper_author.author = mock_author
            authors.append(mock_paper_author)

        mock_paper = self.create_mock_paperoni_paper(authors=authors)

        adapter = PaperoniAdapter()
        simple_paper = adapter.convert(mock_paper)

        assert simple_paper.authors == ["Alice", "Bob", "Charlie"]

    def test_paperoni_adapter_no_pdf_link(self):
        """Test conversion when no PDF link is available"""
        # Create non-PDF links
        links = []
        for link_type in ["html", "abstract", "metadata"]:
            mock_link = Mock()
            mock_link.type = link_type
            mock_link.url = f"https://example.com/{link_type}"
            links.append(mock_link)

        mock_paper = self.create_mock_paperoni_paper(links=links)

        adapter = PaperoniAdapter()
        simple_paper = adapter.convert(mock_paper)
        
        assert simple_paper.pdf_urls == []

    def test_paperoni_adapter_missing_fields(self):
        """Test conversion with missing/empty fields"""
        # Create paper with minimal/missing fields
        mock_paper = Mock()
        mock_paper.title = "Minimal Paper"
        mock_paper.authors = []
        mock_paper.releases = []
        mock_paper.links = []
        mock_paper.abstract = None
        # doi attribute doesn't exist

        adapter = PaperoniAdapter()
        simple_paper = adapter.convert(mock_paper)

        assert simple_paper.title == "Minimal Paper"
        assert simple_paper.authors == []
        assert simple_paper.venue == ""
        assert (
            simple_paper.year == datetime.now().year
        )  # Should default to current year
        assert simple_paper.abstract is None
        assert simple_paper.pdf_urls == []
        assert simple_paper.doi is None

    def test_paperoni_adapter_pdf_link_case_insensitive(self):
        """Test that PDF link detection is case insensitive"""
        mock_link = Mock()
        mock_link.type = "PDF"  # Uppercase
        mock_link.url = "https://example.com/paper.pdf"

        mock_paper = self.create_mock_paperoni_paper(links=[mock_link])

        adapter = PaperoniAdapter()
        simple_paper = adapter.convert(mock_paper)
        
        assert simple_paper.pdf_urls == ["https://example.com/paper.pdf"]


class TestScrapingBatch:
    """Test ScrapingBatch container"""

    def test_scraping_batch_creation(self):
        """Test creating ScrapingBatch with basic data"""
        papers = [
            SimplePaper(
                title=f"Paper {i}",
                authors=[f"Author {i}"],
                venue="TestConf",
                year=2024,
            )
            for i in range(5)
        ]

        batch = ScrapingBatch(
            papers=papers,
            source="test_scraper",
            venue="TestConf",
            year=2024,
            total_found=10,
            successfully_parsed=5,
        )

        assert len(batch.papers) == 5
        assert batch.source == "test_scraper"
        assert batch.venue == "TestConf"
        assert batch.year == 2024
        assert batch.total_found == 10
        assert batch.successfully_parsed == 5
        assert batch.errors == []

    def test_scraping_batch_success_rate(self):
        """Test success rate calculation"""
        batch = ScrapingBatch(
            papers=[],
            source="test",
            venue="Test",
            year=2024,
            total_found=100,
            successfully_parsed=75,
        )

        assert batch.success_rate == 0.75

    def test_scraping_batch_success_rate_zero_found(self):
        """Test success rate when no papers found"""
        batch = ScrapingBatch(
            papers=[],
            source="test",
            venue="Test",
            year=2024,
            total_found=0,
            successfully_parsed=0,
        )

        # Should not divide by zero
        assert batch.success_rate == 0.0

    def test_scraping_batch_with_errors(self):
        """Test ScrapingBatch with error tracking"""
        batch = ScrapingBatch(
            papers=[],
            source="test",
            venue="Test",
            year=2024,
            total_found=10,
            successfully_parsed=7,
            errors=[
                "Failed to parse paper 3: Invalid format",
                "Failed to parse paper 6: Missing title",
                "Failed to parse paper 9: Network error",
            ],
        )

        assert len(batch.errors) == 3
        assert batch.success_rate == 0.7
        assert "Invalid format" in batch.errors[0]
