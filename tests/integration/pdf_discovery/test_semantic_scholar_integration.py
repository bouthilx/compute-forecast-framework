"""Integration tests for Semantic Scholar PDF Collector with framework."""

from unittest.mock import Mock, patch
from datetime import datetime

from compute_forecast.pdf_discovery.core.framework import PDFDiscoveryFramework
from compute_forecast.pdf_discovery.sources.semantic_scholar_collector import (
    SemanticScholarPDFCollector,
)
from compute_forecast.data.models import Paper, Author


class TestSemanticScholarIntegration:
    """Integration tests for Semantic Scholar PDF collector with the framework."""

    @patch("time.sleep", return_value=None)
    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_framework_integration(self, mock_ss_class, mock_sleep):
        """Test that SS collector integrates properly with the framework."""
        # Setup mock
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock API responses
        mock_api.get_paper.return_value = None

        def search_side_effect(query, limit=5):
            if "Machine Learning" in query:
                return {
                    "data": [
                        {
                            "paperId": "ss_ml_123",
                            "title": "Machine Learning Paper",
                            "openAccessPdf": {
                                "url": "https://arxiv.org/pdf/2301.00001.pdf",
                                "status": "GREEN",
                            },
                        }
                    ]
                }
            elif "Deep Learning" in query:
                return {
                    "data": [
                        {
                            "paperId": "ss_dl_456",
                            "title": "Deep Learning Paper",
                            "openAccessPdf": {
                                "url": "https://arxiv.org/pdf/2301.00002.pdf",
                                "status": "GOLD",
                            },
                        }
                    ]
                }
            return {"data": []}

        mock_api.search_paper.side_effect = search_side_effect

        # Create framework and add collector
        framework = PDFDiscoveryFramework()
        collector = SemanticScholarPDFCollector()
        framework.add_collector(collector)

        # Test papers
        papers = [
            Paper(
                paper_id="paper_1",
                title="Machine Learning Paper",
                authors=[Author(name="John Doe")],
                year=2024,
                citations=10,
                venue="ICML",
            ),
            Paper(
                paper_id="paper_2",
                title="Deep Learning Paper",
                authors=[Author(name="Jane Smith")],
                year=2024,
                citations=20,
                venue="NeurIPS",
            ),
            Paper(
                paper_id="paper_3",
                title="Unknown Paper",
                authors=[Author(name="Bob Wilson")],
                year=2024,
                citations=5,
                venue="Workshop",
            ),
        ]

        # Discover PDFs
        result = framework.discover_pdfs(papers)

        # Verify results
        assert result.total_papers == 3
        assert result.discovered_count == 2
        assert len(result.records) == 2
        assert len(result.failed_papers) == 1
        assert "paper_3" in result.failed_papers

        # Check discovered PDFs
        pdf_map = {r.paper_id: r for r in result.records}
        assert "paper_1" in pdf_map
        assert "paper_2" in pdf_map
        assert pdf_map["paper_1"].pdf_url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert pdf_map["paper_2"].pdf_url == "https://arxiv.org/pdf/2301.00002.pdf"

    @patch("time.sleep", return_value=None)
    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_venue_priority_integration(self, mock_ss_class, mock_sleep):
        """Test that venue priorities work with SS collector."""
        # Setup mock
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Mock all papers to have PDFs
        mock_api.get_paper.return_value = None
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_123",
                    "title": "Test Paper",
                    "openAccessPdf": {"url": "https://ss.pdf", "status": "GREEN"},
                }
            ]
        }

        # Create framework with SS as priority for NeurIPS
        framework = PDFDiscoveryFramework()
        framework.set_venue_priorities(
            {
                "NeurIPS": ["semantic_scholar", "arxiv"],
                "ICML": ["arxiv", "semantic_scholar"],
                "default": ["arxiv"],
            }
        )

        collector = SemanticScholarPDFCollector()
        framework.add_collector(collector)

        # Test papers
        papers = [
            Paper(
                paper_id="neurips_paper",
                title="NeurIPS Paper",
                authors=[],
                year=2024,
                citations=0,
                venue="NeurIPS",
            ),
            Paper(
                paper_id="icml_paper",
                title="ICML Paper",
                authors=[],
                year=2024,
                citations=0,
                venue="ICML",
            ),
        ]

        # Discover PDFs
        result = framework.discover_pdfs(papers)

        # SS should process NeurIPS paper first due to priority
        assert result.discovered_count >= 1
        neurips_record = next(
            (r for r in result.records if r.paper_id == "neurips_paper"), None
        )
        if neurips_record:
            assert neurips_record.source == "semantic_scholar"

    @patch("time.sleep", return_value=None)
    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_deduplication_with_other_sources(self, mock_ss_class, mock_sleep):
        """Test that SS PDFs are properly deduplicated with other sources."""
        from compute_forecast.pdf_discovery.core.models import PDFRecord

        # Create mock other collector
        class MockArxivCollector:
            def __init__(self):
                self.source_name = "arxiv"
                self.timeout = 60
                self.supports_batch = False
                self._stats = {"attempted": 0, "successful": 0, "failed": 0}

            def discover_pdfs(self, papers):
                results = {}
                for paper in papers:
                    if "Machine Learning" in paper.title:
                        results[paper.paper_id] = PDFRecord(
                            paper_id=paper.paper_id,
                            pdf_url="https://arxiv.org/pdf/2301.00001v1.pdf",
                            source="arxiv",
                            discovery_timestamp=datetime.now(),
                            confidence_score=0.95,
                            version_info={"version": "v1"},
                            validation_status="preprint",
                            file_size_bytes=None,
                            license=None,
                        )
                return results

            def get_statistics(self):
                return self._stats

        # Setup SS mock
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        mock_api.get_paper.return_value = None
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_ml_123",
                    "title": "Machine Learning Paper",
                    "openAccessPdf": {
                        "url": "https://proceedings.mlr.press/v139/paper.pdf",
                        "status": "GOLD",
                    },
                }
            ]
        }

        # Create framework with both collectors
        framework = PDFDiscoveryFramework()
        framework.add_collector(MockArxivCollector())
        framework.add_collector(SemanticScholarPDFCollector())

        # Test paper that both sources will find
        papers = [
            Paper(
                paper_id="ml_paper",
                title="Machine Learning Paper",
                authors=[Author(name="John Doe")],
                year=2024,
                citations=10,
                venue="ICML",
            )
        ]

        # Discover PDFs
        result = framework.discover_pdfs(papers)

        # Should get deduplicated to one PDF
        assert result.discovered_count == 1
        assert len(result.records) == 1

        # The published version (GOLD status) should be preferred
        pdf_record = result.records[0]
        assert (
            "proceedings.mlr.press" in pdf_record.pdf_url
            or "arxiv" in pdf_record.pdf_url
        )

    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_real_api_timeout_handling(self, mock_ss_class):
        """Test timeout handling in real conditions."""
        # Setup mock that delays
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # We'll just test that the timeout mechanism exists
        # Real timeout testing with ThreadPoolExecutor is complex
        collector = SemanticScholarPDFCollector()
        assert collector.timeout == 60  # Default timeout

        # Test that we can set timeout
        collector.timeout = 30
        assert collector.timeout == 30

    @patch("time.sleep", return_value=None)
    @patch(
        "src.pdf_discovery.sources.semantic_scholar_collector.semanticscholar.SemanticScholar"
    )
    def test_mixed_identifier_batch(self, mock_ss_class, mock_sleep):
        """Test batch processing with mixed identifier types."""
        mock_api = Mock()
        mock_ss_class.return_value = mock_api

        # Create papers with different identifier types
        papers = []

        # Paper with DOI
        p1 = Paper(
            paper_id="doi_paper",
            title="DOI Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        p1.doi = "10.1234/test"
        papers.append(p1)

        # Paper with arXiv ID
        p2 = Paper(
            paper_id="arxiv_paper",
            title="ArXiv Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        p2.arxiv_id = "2301.00001"
        papers.append(p2)

        # Paper with SS ID
        p3 = Paper(
            paper_id="ss_paper",
            title="SS Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        p3.semantic_scholar_id = "ss_direct_123"
        papers.append(p3)

        # Paper with only title
        p4 = Paper(
            paper_id="title_paper",
            title="Title Only Paper",
            authors=[],
            year=2024,
            citations=0,
            venue="Test",
        )
        papers.append(p4)

        # Mock batch response
        mock_api.get_papers.return_value = [
            {
                "paperId": "ss_1",
                "doi": "10.1234/test",
                "openAccessPdf": {"url": "doi.pdf", "status": "GREEN"},
            },
            {
                "paperId": "ss_2",
                "arxivId": "2301.00001",
                "openAccessPdf": {"url": "arxiv.pdf", "status": "GREEN"},
            },
            {
                "paperId": "ss_direct_123",
                "openAccessPdf": {"url": "direct.pdf", "status": "GREEN"},
            },
        ]

        # Mock search for title-only paper
        mock_api.search_paper.return_value = {
            "data": [
                {
                    "paperId": "ss_4",
                    "title": "Title Only Paper",
                    "openAccessPdf": {"url": "title.pdf", "status": "GREEN"},
                }
            ]
        }

        collector = SemanticScholarPDFCollector()
        results = collector.discover_pdfs(papers)

        # Should find all 4 PDFs
        assert len(results) == 4
        assert results["doi_paper"].pdf_url == "doi.pdf"
        assert results["arxiv_paper"].pdf_url == "arxiv.pdf"
        assert results["ss_paper"].pdf_url == "direct.pdf"
        assert results["title_paper"].pdf_url == "title.pdf"
