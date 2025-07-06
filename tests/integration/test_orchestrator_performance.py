"""Integration tests for enhanced orchestrator performance validation."""

import asyncio
import time
from unittest.mock import patch
import pytest
from compute_forecast.data.collectors.enhanced_orchestrator import (
    EnhancedCollectionOrchestrator as EnhancedOrchestrator,
)


class TestOrchestratorPerformance:
    """Test performance improvements of parallel vs sequential collection."""

    @pytest.fixture
    def mock_responses(self):
        """Create mock API responses for each source."""
        return {
            "semantic_scholar": {
                "data": [
                    {"paperId": "1", "title": "Paper 1", "year": 2023},
                    {"paperId": "2", "title": "Paper 2", "year": 2023},
                ],
                "total": 2,
            },
            "openalex": {
                "results": [
                    {"id": "W1", "title": "Paper 3", "publication_year": 2023},
                    {"id": "W2", "title": "Paper 4", "publication_year": 2023},
                ],
                "meta": {"count": 2},
            },
            "crossref": {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1/1",
                            "title": ["Paper 5"],
                            "published-print": {"date-parts": [[2023]]},
                        },
                        {
                            "DOI": "10.1/2",
                            "title": ["Paper 6"],
                            "published-print": {"date-parts": [[2023]]},
                        },
                    ],
                    "total-results": 2,
                }
            },
            "google_scholar": [
                {"title": "Paper 7", "link": "http://example.com/7", "year": "2023"},
                {"title": "Paper 8", "link": "http://example.com/8", "year": "2023"},
            ],
        }

    @pytest.fixture
    def mock_delay_responses(self):
        """Create delayed mock responses to simulate API latency."""

        async def delayed_response(data, delay=0.5):
            await asyncio.sleep(delay)
            return data

        return delayed_response

    @pytest.mark.asyncio
    async def test_parallel_performance_improvement(
        self, mock_responses, mock_delay_responses
    ):
        """Test that parallel collection is at least 60% faster than sequential."""
        orchestrator = EnhancedOrchestrator()

        # Mock each source with delayed responses
        with patch(
            "src.data.sources.semantic_scholar.SemanticScholarSource.search"
        ) as mock_ss, patch(
            "src.data.sources.openalex.OpenAlexSource.search"
        ) as mock_oa, patch(
            "src.data.sources.crossref.CrossRefSource.search"
        ) as mock_cr, patch(
            "src.data.sources.google_scholar.GoogleScholarSource.search"
        ) as mock_gs:
            # Configure mocks with delays to simulate real API calls
            mock_ss.return_value = await mock_delay_responses(
                mock_responses["semantic_scholar"], 0.5
            )
            mock_oa.return_value = await mock_delay_responses(
                mock_responses["openalex"], 0.5
            )
            mock_cr.return_value = await mock_delay_responses(
                mock_responses["crossref"], 0.5
            )
            mock_gs.return_value = await mock_delay_responses(
                mock_responses["google_scholar"], 0.5
            )

            # Test sequential collection
            start_sequential = time.time()
            sequential_results = await orchestrator.collect_sequential(
                "machine learning", max_results=10
            )
            sequential_time = time.time() - start_sequential

            # Reset mocks
            mock_ss.reset_mock()
            mock_oa.reset_mock()
            mock_cr.reset_mock()
            mock_gs.reset_mock()

            # Configure mocks again for parallel test
            mock_ss.return_value = await mock_delay_responses(
                mock_responses["semantic_scholar"], 0.5
            )
            mock_oa.return_value = await mock_delay_responses(
                mock_responses["openalex"], 0.5
            )
            mock_cr.return_value = await mock_delay_responses(
                mock_responses["crossref"], 0.5
            )
            mock_gs.return_value = await mock_delay_responses(
                mock_responses["google_scholar"], 0.5
            )

            # Test parallel collection
            start_parallel = time.time()
            parallel_results = await orchestrator.collect_parallel(
                "machine learning", max_results=10
            )
            parallel_time = time.time() - start_parallel

            # Calculate performance improvement
            improvement = ((sequential_time - parallel_time) / sequential_time) * 100

            # Assertions
            assert (
                improvement >= 60
            ), f"Expected at least 60% improvement, got {improvement:.1f}%"
            assert len(parallel_results["papers"]) == len(sequential_results["papers"])
            assert (
                parallel_results["total_results"] == sequential_results["total_results"]
            )

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, mock_responses):
        """Test that rate limiting is properly enforced for each source."""
        orchestrator = EnhancedOrchestrator()

        with patch(
            "src.data.sources.google_scholar.GoogleScholarSource.search"
        ) as mock_gs:
            # Track call times
            call_times = []

            async def track_calls(*args, **kwargs):
                call_times.append(time.time())
                return mock_responses["google_scholar"]

            mock_gs.side_effect = track_calls

            # Make multiple searches to trigger rate limiting
            for _ in range(3):
                await orchestrator.sources["google_scholar"].search(
                    "test query", max_results=5
                )

            # Check that calls are properly spaced (Google Scholar has 2s delay)
            if len(call_times) > 1:
                for i in range(1, len(call_times)):
                    time_diff = call_times[i] - call_times[i - 1]
                    assert (
                        time_diff >= 1.9
                    ), f"Rate limit not enforced: {time_diff}s between calls"

    @pytest.mark.asyncio
    async def test_error_handling_with_fallbacks(self, mock_responses):
        """Test that errors in one source don't affect others."""
        orchestrator = EnhancedOrchestrator()

        with patch(
            "src.data.sources.semantic_scholar.SemanticScholarSource.search"
        ) as mock_ss, patch(
            "src.data.sources.openalex.OpenAlexSource.search"
        ) as mock_oa, patch(
            "src.data.sources.crossref.CrossRefSource.search"
        ) as mock_cr, patch(
            "src.data.sources.google_scholar.GoogleScholarSource.search"
        ) as mock_gs:
            # Make one source fail
            mock_ss.side_effect = Exception("API Error")
            mock_oa.return_value = mock_responses["openalex"]
            mock_cr.return_value = mock_responses["crossref"]
            mock_gs.return_value = mock_responses["google_scholar"]

            # Collect should still work with 3 sources
            results = await orchestrator.collect_parallel("test query", max_results=10)

            # Should have results from 3 sources (2 papers each)
            assert len(results["papers"]) == 6
            assert len(results["errors"]) == 1
            assert "semantic_scholar" in results["errors"]

    @pytest.mark.asyncio
    async def test_mock_api_responses_validity(self, mock_responses):
        """Validate that mock responses match expected API formats."""
        orchestrator = EnhancedOrchestrator()

        # Test Semantic Scholar format
        ss_response = mock_responses["semantic_scholar"]
        assert "data" in ss_response
        assert all(
            key in paper
            for paper in ss_response["data"]
            for key in ["paperId", "title", "year"]
        )

        # Test OpenAlex format
        oa_response = mock_responses["openalex"]
        assert "results" in oa_response
        assert all(
            key in paper
            for paper in oa_response["results"]
            for key in ["id", "title", "publication_year"]
        )

        # Test CrossRef format
        cr_response = mock_responses["crossref"]
        assert "message" in cr_response
        assert "items" in cr_response["message"]
        assert all(
            key in paper
            for paper in cr_response["message"]["items"]
            for key in ["DOI", "title"]
        )

        # Test Google Scholar format
        gs_response = mock_responses["google_scholar"]
        assert isinstance(gs_response, list)
        assert all(
            key in paper for paper in gs_response for key in ["title", "link", "year"]
        )
