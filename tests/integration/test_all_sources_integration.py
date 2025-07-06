"""End-to-end integration tests for all 4 academic sources."""

import asyncio
from datetime import datetime
from unittest.mock import patch
import pytest
from compute_forecast.data.collectors.enhanced_orchestrator import (
    EnhancedCollectionOrchestrator as EnhancedOrchestrator,
)


class TestAllSourcesIntegration:
    """Test all 4 sources working together in realistic scenarios."""

    @pytest.fixture
    def comprehensive_mock_data(self):
        """Create comprehensive mock data simulating real API responses."""
        return {
            "semantic_scholar": {
                "data": [
                    {
                        "paperId": "ss1",
                        "title": "Deep Learning for Natural Language Processing",
                        "abstract": "A comprehensive survey of deep learning techniques...",
                        "year": 2023,
                        "authors": [{"name": "John Doe"}, {"name": "Jane Smith"}],
                        "citationCount": 150,
                        "url": "https://semanticscholar.org/paper/ss1",
                    },
                    {
                        "paperId": "ss2",
                        "title": "Transformer Architecture: A Review",
                        "abstract": "This paper reviews the transformer architecture...",
                        "year": 2023,
                        "authors": [{"name": "Alice Brown"}],
                        "citationCount": 200,
                        "url": "https://semanticscholar.org/paper/ss2",
                    },
                ],
                "total": 2,
            },
            "openalex": {
                "results": [
                    {
                        "id": "W1234567890",
                        "title": "Machine Learning in Healthcare Applications",
                        "abstract": "This study explores ML applications in healthcare...",
                        "publication_year": 2023,
                        "authorships": [
                            {"author": {"display_name": "Bob Johnson"}},
                            {"author": {"display_name": "Carol White"}},
                        ],
                        "cited_by_count": 75,
                        "doi": "10.1234/healthcare.2023.001",
                    },
                    {
                        "id": "W0987654321",
                        "title": "Federated Learning: Privacy-Preserving ML",
                        "abstract": "A survey on federated learning techniques...",
                        "publication_year": 2023,
                        "authorships": [{"author": {"display_name": "David Lee"}}],
                        "cited_by_count": 100,
                        "doi": "10.1234/federated.2023.002",
                    },
                ],
                "meta": {"count": 2},
            },
            "crossref": {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1109/TPAMI.2023.1234567",
                            "title": [
                                "Computer Vision with Deep Learning: Recent Advances"
                            ],
                            "abstract": "This paper presents recent advances in computer vision...",
                            "published-print": {"date-parts": [[2023, 6, 15]]},
                            "author": [
                                {"given": "Eva", "family": "Martinez"},
                                {"given": "Frank", "family": "Chen"},
                            ],
                            "is-referenced-by-count": 120,
                            "URL": "https://doi.org/10.1109/TPAMI.2023.1234567",
                        },
                        {
                            "DOI": "10.1145/3456789.2023.001",
                            "title": ["Reinforcement Learning in Robotics"],
                            "abstract": "A comprehensive review of RL applications...",
                            "published-print": {"date-parts": [[2023, 8, 20]]},
                            "author": [{"given": "George", "family": "Wilson"}],
                            "is-referenced-by-count": 90,
                            "URL": "https://doi.org/10.1145/3456789.2023.001",
                        },
                    ],
                    "total-results": 2,
                }
            },
            "google_scholar": [
                {
                    "title": "Neural Architecture Search: A Survey",
                    "link": "https://arxiv.org/abs/2301.12345",
                    "year": "2023",
                    "authors": "H Zhang, I Brown",
                    "snippet": "This survey provides a comprehensive overview of neural architecture search...",
                    "citations": "Cited by 180",
                },
                {
                    "title": "Graph Neural Networks for Social Networks",
                    "link": "https://arxiv.org/abs/2302.67890",
                    "year": "2023",
                    "authors": "J Taylor, K Davis",
                    "snippet": "We present a novel approach using graph neural networks...",
                    "citations": "Cited by 95",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_all_sources_collect_successfully(self, comprehensive_mock_data):
        """Test that all 4 sources can be collected and combined successfully."""
        orchestrator = EnhancedOrchestrator()

        with (
            patch(
                "src.data.sources.semantic_scholar.SemanticScholarSource.search"
            ) as mock_ss,
            patch("src.data.sources.openalex.OpenAlexSource.search") as mock_oa,
            patch("src.data.sources.crossref.CrossRefSource.search") as mock_cr,
            patch(
                "src.data.sources.google_scholar.GoogleScholarSource.search"
            ) as mock_gs,
        ):
            # Configure all mocks
            mock_ss.return_value = comprehensive_mock_data["semantic_scholar"]
            mock_oa.return_value = comprehensive_mock_data["openalex"]
            mock_cr.return_value = comprehensive_mock_data["crossref"]
            mock_gs.return_value = comprehensive_mock_data["google_scholar"]

            # Collect from all sources
            results = await orchestrator.collect_parallel(
                "machine learning", max_results=20
            )

            # Verify results
            assert results["total_results"] == 8  # 2 from each source
            assert len(results["papers"]) == 8
            assert len(results["errors"]) == 0
            assert results["sources_queried"] == [
                "semantic_scholar",
                "openalex",
                "crossref",
                "google_scholar",
            ]

            # Verify each source contributed papers
            source_counts = {}
            for paper in results["papers"]:
                source = paper.get("source", "unknown")
                source_counts[source] = source_counts.get(source, 0) + 1

            assert source_counts.get("semantic_scholar", 0) == 2
            assert source_counts.get("openalex", 0) == 2
            assert source_counts.get("crossref", 0) == 2
            assert source_counts.get("google_scholar", 0) == 2

    @pytest.mark.asyncio
    async def test_unified_paper_format(self, comprehensive_mock_data):
        """Test that papers from all sources are normalized to a unified format."""
        orchestrator = EnhancedOrchestrator()

        with (
            patch(
                "src.data.sources.semantic_scholar.SemanticScholarSource.search"
            ) as mock_ss,
            patch("src.data.sources.openalex.OpenAlexSource.search") as mock_oa,
            patch("src.data.sources.crossref.CrossRefSource.search") as mock_cr,
            patch(
                "src.data.sources.google_scholar.GoogleScholarSource.search"
            ) as mock_gs,
        ):
            mock_ss.return_value = comprehensive_mock_data["semantic_scholar"]
            mock_oa.return_value = comprehensive_mock_data["openalex"]
            mock_cr.return_value = comprehensive_mock_data["crossref"]
            mock_gs.return_value = comprehensive_mock_data["google_scholar"]

            results = await orchestrator.collect_parallel(
                "machine learning", max_results=20
            )

            # Check that all papers have required fields
            required_fields = ["title", "year", "source", "url"]
            for paper in results["papers"]:
                for field in required_fields:
                    assert (
                        field in paper
                    ), f"Paper missing required field '{field}': {paper}"

                # Verify year is integer
                assert isinstance(
                    paper["year"], int
                ), f"Year should be int: {paper['year']}"

                # Verify source is valid
                assert paper["source"] in [
                    "semantic_scholar",
                    "openalex",
                    "crossref",
                    "google_scholar",
                ]

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, comprehensive_mock_data):
        """Test that rate limiting works correctly when all sources are queried concurrently."""
        orchestrator = EnhancedOrchestrator()

        # Track API call times for each source
        call_times = {
            "semantic_scholar": [],
            "openalex": [],
            "crossref": [],
            "google_scholar": [],
        }

        async def track_ss_calls(*args, **kwargs):
            call_times["semantic_scholar"].append(datetime.now())
            return comprehensive_mock_data["semantic_scholar"]

        async def track_oa_calls(*args, **kwargs):
            call_times["openalex"].append(datetime.now())
            return comprehensive_mock_data["openalex"]

        async def track_cr_calls(*args, **kwargs):
            call_times["crossref"].append(datetime.now())
            return comprehensive_mock_data["crossref"]

        async def track_gs_calls(*args, **kwargs):
            call_times["google_scholar"].append(datetime.now())
            await asyncio.sleep(2)  # Google Scholar has 2s rate limit
            return comprehensive_mock_data["google_scholar"]

        with (
            patch(
                "src.data.sources.semantic_scholar.SemanticScholarSource.search",
                side_effect=track_ss_calls,
            ),
            patch(
                "src.data.sources.openalex.OpenAlexSource.search",
                side_effect=track_oa_calls,
            ),
            patch(
                "src.data.sources.crossref.CrossRefSource.search",
                side_effect=track_cr_calls,
            ),
            patch(
                "src.data.sources.google_scholar.GoogleScholarSource.search",
                side_effect=track_gs_calls,
            ),
        ):
            # Make multiple concurrent searches
            tasks = []
            for i in range(3):
                task = orchestrator.collect_parallel(f"query {i}", max_results=5)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # Verify all searches completed
            assert len(results) == 3
            for result in results:
                assert result["total_results"] > 0

    @pytest.mark.asyncio
    async def test_partial_source_failure_handling(self, comprehensive_mock_data):
        """Test system resilience when some sources fail."""
        orchestrator = EnhancedOrchestrator()

        scenarios = [
            # Scenario 1: One source fails
            {"failing_sources": ["semantic_scholar"], "expected_papers": 6},
            # Scenario 2: Two sources fail
            {"failing_sources": ["openalex", "crossref"], "expected_papers": 4},
            # Scenario 3: Three sources fail
            {
                "failing_sources": ["semantic_scholar", "openalex", "crossref"],
                "expected_papers": 2,
            },
        ]

        for scenario in scenarios:
            with (
                patch(
                    "src.data.sources.semantic_scholar.SemanticScholarSource.search"
                ) as mock_ss,
                patch("src.data.sources.openalex.OpenAlexSource.search") as mock_oa,
                patch("src.data.sources.crossref.CrossRefSource.search") as mock_cr,
                patch(
                    "src.data.sources.google_scholar.GoogleScholarSource.search"
                ) as mock_gs,
            ):
                # Configure mocks based on scenario
                if "semantic_scholar" in scenario["failing_sources"]:
                    mock_ss.side_effect = Exception("API Error")
                else:
                    mock_ss.return_value = comprehensive_mock_data["semantic_scholar"]

                if "openalex" in scenario["failing_sources"]:
                    mock_oa.side_effect = Exception("API Error")
                else:
                    mock_oa.return_value = comprehensive_mock_data["openalex"]

                if "crossref" in scenario["failing_sources"]:
                    mock_cr.side_effect = Exception("API Error")
                else:
                    mock_cr.return_value = comprehensive_mock_data["crossref"]

                if "google_scholar" in scenario["failing_sources"]:
                    mock_gs.side_effect = Exception("API Error")
                else:
                    mock_gs.return_value = comprehensive_mock_data["google_scholar"]

                # Collect and verify
                results = await orchestrator.collect_parallel(
                    "test query", max_results=20
                )

                assert len(results["papers"]) == scenario["expected_papers"]
                assert len(results["errors"]) == len(scenario["failing_sources"])

                for source in scenario["failing_sources"]:
                    assert source in results["errors"]

    @pytest.mark.asyncio
    async def test_search_query_consistency(self, comprehensive_mock_data):
        """Test that the same query produces consistent results across sources."""
        orchestrator = EnhancedOrchestrator()
        query = "deep learning transformer architecture"

        with (
            patch(
                "src.data.sources.semantic_scholar.SemanticScholarSource.search"
            ) as mock_ss,
            patch("src.data.sources.openalex.OpenAlexSource.search") as mock_oa,
            patch("src.data.sources.crossref.CrossRefSource.search") as mock_cr,
            patch(
                "src.data.sources.google_scholar.GoogleScholarSource.search"
            ) as mock_gs,
        ):
            mock_ss.return_value = comprehensive_mock_data["semantic_scholar"]
            mock_oa.return_value = comprehensive_mock_data["openalex"]
            mock_cr.return_value = comprehensive_mock_data["crossref"]
            mock_gs.return_value = comprehensive_mock_data["google_scholar"]

            # Run the same query multiple times
            results1 = await orchestrator.collect_parallel(query, max_results=20)
            results2 = await orchestrator.collect_parallel(query, max_results=20)

            # Results should be consistent
            assert results1["total_results"] == results2["total_results"]
            assert len(results1["papers"]) == len(results2["papers"])

            # Verify each source was called with the correct query
            mock_ss.assert_called_with(query, max_results=5)
            mock_oa.assert_called_with(query, max_results=5)
            mock_cr.assert_called_with(query, max_results=5)
            mock_gs.assert_called_with(query, max_results=5)
