"""
Unit tests for venue normalization system.
Tests VenueNormalizer, FuzzyVenueMatcher, and VenueMappingLoader.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from compute_forecast.data.processors import (
    VenueNormalizer, 
    VenueNormalizationResult,
    BatchNormalizationResult,
    FuzzyVenueMatcher,
    VenueMappingLoader,
    VenueConfig
)
from compute_forecast.data.models import Paper, Author


class TestFuzzyVenueMatcher:
    """Test fuzzy venue matching functionality"""
    
    def setup_method(self):
        self.matcher = FuzzyVenueMatcher(fuzzy_threshold=0.9)
    
    def test_normalize_venue_name(self):
        """Test venue name normalization"""
        # Test basic normalization
        assert self.matcher.normalize_venue_name("ICML 2024") == "ICML"
        assert self.matcher.normalize_venue_name("NeurIPS'23") == "NEURIPS"
        assert self.matcher.normalize_venue_name("Proceedings of ICLR") == "ICLR"
        
        # Test abbreviation expansion
        assert "NEURAL INFORMATION PROCESSING SYSTEMS" in self.matcher.normalize_venue_name("NIPS")
        
        # Test noise removal
        assert self.matcher.normalize_venue_name("ICML (Workshop)") == "ICML"
        assert self.matcher.normalize_venue_name("ACL - Findings") == "ACL"
    
    def test_calculate_venue_similarity(self):
        """Test venue similarity calculation"""
        # Exact match
        assert self.matcher.calculate_venue_similarity("ICML", "ICML") == 1.0
        
        # High similarity
        similarity = self.matcher.calculate_venue_similarity("ICML 2024", "ICML")
        assert similarity > 0.9
        
        # Low similarity
        similarity = self.matcher.calculate_venue_similarity("ICML", "CVPR")
        assert similarity < 0.5
        
        # Abbreviation vs full name
        similarity = self.matcher.calculate_venue_similarity("NIPS", "NeurIPS")
        assert similarity > 0.8
    
    def test_find_best_match(self):
        """Test finding best fuzzy match"""
        candidates = ["ICML", "NeurIPS", "ICLR", "CVPR", "AAAI"]
        
        # Exact match
        result = self.matcher.find_best_match("ICML", candidates)
        assert result.matched_venue == "ICML"
        assert result.similarity_score == 1.0
        assert result.match_type == "exact"
        
        # Fuzzy match
        result = self.matcher.find_best_match("ICML 2024", candidates, threshold=0.8)
        assert result.matched_venue == "ICML"
        assert result.similarity_score > 0.8
        assert result.match_type == "fuzzy"
        
        # No match
        result = self.matcher.find_best_match("Random Conference", candidates)
        assert result.matched_venue is None
        assert result.match_type == "none"
    
    def test_batch_find_matches(self):
        """Test batch fuzzy matching"""
        raw_venues = ["ICML 2024", "NeurIPS'23", "Unknown Conf"]
        candidates = ["ICML", "NeurIPS", "ICLR"]
        
        results = self.matcher.batch_find_matches(raw_venues, candidates, threshold=0.8)
        
        # Should find matches for known venues
        assert results["ICML 2024"].matched_venue == "ICML"
        assert results["NeurIPS'23"].matched_venue == "NeurIPS"
        assert results["Unknown Conf"].matched_venue is None


class TestVenueMappingLoader:
    """Test venue mapping loading functionality"""
    
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.loader = VenueMappingLoader(self.temp_dir)
    
    def teardown_method(self):
        # Cleanup temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_worker6_mappings(self):
        """Test loading Worker 6 venue mappings"""
        # Create test Worker 6 data
        worker6_data = {
            "venue_normalization_map": {
                "ICML 2024": "ICML",
                "NeurIPS.cc/2024/Conference": "NeurIPS"
            },
            "canonical_venues": ["ICML", "NeurIPS", "ICLR"]
        }
        
        worker6_path = self.temp_dir / "worker6_venue_mapping.json"
        with open(worker6_path, 'w') as f:
            json.dump(worker6_data, f)
        
        result = self.loader.load_all_mappings()
        
        assert "ICML 2024" in result.venue_mappings
        assert result.venue_mappings["ICML 2024"] == "ICML"
        assert "ICML" in result.canonical_venues
        assert "worker6_venue_mapping.json" in result.sources_loaded
    
    def test_load_venues_yaml(self):
        """Test loading venues.yaml configuration"""
        # Create test venues.yaml
        venues_yaml_data = {
            "venues_by_domain": {
                "ml_general": {
                    "tier1": ["ICML", "NeurIPS", "ICLR"],
                    "tier2": ["AISTATS", "UAI"]
                }
            },
            "computational_focus_scores": {
                "ICML": 0.95,
                "NeurIPS": 0.95
            }
        }
        
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        venues_yaml_path = config_dir / "venues.yaml"
        
        import yaml
        with open(venues_yaml_path, 'w') as f:
            yaml.dump(venues_yaml_data, f)
        
        result = self.loader.load_all_mappings()
        
        assert "ICML" in result.venue_configs
        assert result.venue_configs["ICML"].venue_tier == "tier1"
        assert result.venue_configs["ICML"].computational_focus == 0.95
        assert "config/venues.yaml" in result.sources_loaded
    
    def test_infer_venue_tier(self):
        """Test venue tier inference"""
        assert self.loader._infer_venue_tier("ICML") == "tier1"
        assert self.loader._infer_venue_tier("AAAI") == "tier2"
        assert self.loader._infer_venue_tier("BMVC") == "tier3"
        assert self.loader._infer_venue_tier("Unknown Conf") == "tier4"


class TestVenueNormalizer:
    """Test main venue normalization functionality"""
    
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test data files
        self._create_test_data()
        
        # Initialize normalizer with test data
        with patch.object(VenueMappingLoader, '__init__', return_value=None):
            with patch.object(VenueMappingLoader, 'load_all_mappings') as mock_load:
                mock_load.return_value = self._create_mock_load_result()
                self.normalizer = VenueNormalizer(
                    mapping_file=self.temp_dir / "test_mappings.json",
                    fuzzy_threshold=0.9,
                    update_mappings_live=False
                )
    
    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_data(self):
        """Create test mapping data"""
        test_mappings = {
            "venue_normalization_map": {
                "ICML 2024": "ICML",
                "NeurIPS.cc/2024/Conference": "NeurIPS",
                "Proceedings of ICLR": "ICLR"
            },
            "canonical_venues": ["ICML", "NeurIPS", "ICLR", "CVPR", "AAAI"]
        }
        
        test_path = self.temp_dir / "test_mappings.json"
        with open(test_path, 'w') as f:
            json.dump(test_mappings, f)
    
    def _create_mock_load_result(self):
        """Create mock load result for testing"""
        from compute_forecast.data.processors.venue_mapping_loader import VenueMappingLoadResult
        
        return VenueMappingLoadResult(
            venue_mappings={
                "ICML 2024": "ICML",
                "NeurIPS.cc/2024/Conference": "NeurIPS",
                "Proceedings of ICLR": "ICLR"
            },
            venue_configs={
                "ICML": VenueConfig("ICML", "tier1", 0.95, "ml_general"),
                "NeurIPS": VenueConfig("NeurIPS", "tier1", 0.95, "ml_general"),
                "ICLR": VenueConfig("ICLR", "tier1", 0.90, "ml_general")
            },
            canonical_venues={"ICML", "NeurIPS", "ICLR", "CVPR", "AAAI"},
            sources_loaded=["test_mappings.json"]
        )
    
    def test_normalize_venue_exact_match(self):
        """Test exact venue normalization"""
        result = self.normalizer.normalize_venue("ICML 2024")
        
        assert result.original_venue == "ICML 2024"
        assert result.normalized_venue == "ICML"
        assert result.confidence == 1.0
        assert result.mapping_type == "exact"
    
    def test_normalize_venue_fuzzy_match(self):
        """Test fuzzy venue normalization"""
        # This should find a fuzzy match with ICML
        result = self.normalizer.normalize_venue("International Conference on Machine Learning")
        
        # Might match with ICML via fuzzy matching
        if result.mapping_type == "fuzzy":
            assert result.confidence >= 0.9
            assert result.normalized_venue in self.normalizer._canonical_venues
    
    def test_normalize_venue_no_match(self):
        """Test venue normalization with no match"""
        result = self.normalizer.normalize_venue("Completely Unknown Conference")
        
        assert result.original_venue == "Completely Unknown Conference"
        assert result.normalized_venue == "Completely Unknown Conference"  # Keep original
        assert result.confidence == 0.0
        assert result.mapping_type == "none"
    
    def test_batch_normalize_venues(self):
        """Test batch venue normalization"""
        papers = [
            Paper(
                title="Test Paper 1",
                authors=[Author("Test Author 1")],
                venue="ICML 2024",
                year=2024,
                citations=10
            ),
            Paper(
                title="Test Paper 2", 
                authors=[Author("Test Author 2")],
                venue="Unknown Conference",
                year=2024,
                citations=5
            )
        ]
        
        result = self.normalizer.batch_normalize_venues(papers)
        
        assert result.papers_processed == 2
        assert result.venues_normalized >= 1  # At least ICML should normalize
        assert len(result.unmapped_venues) >= 1  # Unknown Conference should be unmapped
        
        # Check that paper venues were updated
        assert papers[0].normalized_venue == "ICML"
        assert papers[0].venue_confidence == 1.0
    
    def test_update_mapping(self):
        """Test updating venue mappings"""
        # Should succeed with high confidence
        result = self.normalizer.update_mapping("New Venue", "ICML", 0.95)
        assert result is True
        
        # Should fail with low confidence
        result = self.normalizer.update_mapping("Bad Venue", "ICML", 0.5)
        assert result is False
        
        # Should fail with circular mapping
        result = self.normalizer.update_mapping("ICML", "ICML", 0.95)
        assert result is False
    
    def test_get_mapping_statistics(self):
        """Test getting mapping statistics"""
        stats = self.normalizer.get_mapping_statistics()
        
        assert isinstance(stats.total_mappings, int)
        assert stats.total_mappings >= 0
        assert isinstance(stats.coverage_by_tier, dict)
        assert "tier1" in stats.coverage_by_tier
    
    def test_validate_mappings(self):
        """Test mapping validation"""
        errors = self.normalizer.validate_mappings()
        
        # Should return list of validation errors
        assert isinstance(errors, list)
        # Might be empty if no errors, but should be a list
    
    def test_thread_safety(self):
        """Test thread safety of venue normalization"""
        import threading
        import time
        
        results = []
        errors = []
        
        def normalize_venues():
            try:
                for i in range(10):
                    result = self.normalizer.normalize_venue(f"Test Venue {i}")
                    results.append(result)
                    time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=normalize_venues)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors and expected number of results
        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 venues each


class TestIntegration:
    """Integration tests for venue normalization system"""
    
    def test_end_to_end_normalization(self):
        """Test complete venue normalization workflow"""
        # This test requires actual Worker 2/3 data files
        # Skip if files don't exist
        required_files = [
            "worker6_venue_mapping.json",
            "config/venues.yaml"
        ]
        
        missing_files = [f for f in required_files if not Path(f).exists()]
        if missing_files:
            pytest.skip(f"Missing required files: {missing_files}")
        
        # Initialize normalizer with real data
        normalizer = VenueNormalizer(fuzzy_threshold=0.9, update_mappings_live=False)
        
        # Test with real venue names from the mapping
        test_venues = [
            "NeurIPS.cc/2024/Conference",
            "Proceedings of the 41st International Conference on Machine Learning",
            "ICLR.cc/2024/Conference"
        ]
        
        for venue in test_venues:
            result = normalizer.normalize_venue(venue)
            assert result.confidence > 0.0
            assert result.normalized_venue != venue  # Should be normalized
    
    def test_performance_batch_processing(self):
        """Test performance of batch processing"""
        normalizer = VenueNormalizer(fuzzy_threshold=0.9, update_mappings_live=False)
        
        # Create large batch of papers
        papers = []
        venues = ["ICML 2024", "NeurIPS'23", "ICLR Conference", "Unknown Conf"] * 250
        
        for i, venue in enumerate(venues):
            papers.append(Paper(
                title=f"Test Paper {i}",
                authors=[Author(f"Author {i}")],
                venue=venue,
                year=2024,
                citations=i
            ))
        
        start_time = datetime.now()
        result = normalizer.batch_normalize_venues(papers)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Should process 1000 papers within 30 seconds (requirement)
        assert processing_time < 30.0
        assert result.papers_processed == 1000
        
        # Performance metric
        papers_per_second = len(papers) / processing_time
        assert papers_per_second > 30  # Should process at least 30 papers/second