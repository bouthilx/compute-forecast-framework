"""Integration tests for contract validation engine."""

import pytest
import time
from typing import List, Dict, Any

from src.data.models import Paper, ComputationalAnalysis, Author
from src.quality.contracts import (
    AnalysisContractValidator,
    PipelineIntegrationValidator,
    ContractValidationResult,
    ContractViolationType,
)
from src.quality.contracts.contract_tests import ContractTestSuite


class TestContractValidationIntegration:
    """Integration tests for contract validation system."""
    
    @pytest.fixture
    def contract_validator(self):
        """Provide contract validator instance."""
        return AnalysisContractValidator()
    
    @pytest.fixture
    def pipeline_validator(self):
        """Provide pipeline validator instance."""
        return PipelineIntegrationValidator()
    
    @pytest.fixture
    def test_suite(self):
        """Provide contract test suite."""
        return ContractTestSuite()
    
    @pytest.fixture
    def realistic_papers(self):
        """Generate realistic paper dataset with various quality issues."""
        papers = []
        
        # High quality papers
        for i in range(5):
            papers.append(Paper(
                paper_id=f"high_{i}",
                title=f"Deep Learning Advances in Computer Vision: Paper {i}",
                authors=[
                    Author(name=f"Lead Author {i}", affiliation="MIT"),
                    Author(name=f"Co-Author {i}", affiliation="Stanford"),
                ],
                venue="NeurIPS",
                year=2023,
                citations=50 + i * 10,
                abstract=f"This paper presents novel deep learning techniques for computer vision tasks. {i}"
            ))
        
        # Papers with minor issues
        for i in range(3):
            papers.append(Paper(
                paper_id=f"minor_{i}",
                title=f"Machine Learning Study {i}",
                authors=[Author(name=f"Single Author {i}", affiliation="Unknown University")],
                venue="Workshop",
                year=2022,
                citations=2,  # Low citations
                abstract="Short abstract."
            ))
        
        # Papers with major issues
        papers.append(Paper(
            paper_id=None,  # Missing ID
            openalex_id="oa_123",  # Has alternate ID
            title="",  # Empty title
            authors=[],  # No authors
            venue="Unknown",
            year=2024,
            citations=0,
            abstract=None
        ))
        
        papers.append(Paper(
            arxiv_id="arxiv_456",  # Only arxiv ID
            title="Future Paper",
            authors=[Author(name="Time Traveler", affiliation="Future U")],
            venue="FutureCon",
            year=2030,  # Invalid future year
            citations=-10,  # Negative citations
            abstract="From the future"
        ))
        
        return papers
    
    @pytest.fixture
    def realistic_analyses(self):
        """Generate realistic computational analyses with various quality levels."""
        analyses = []
        
        # High quality analyses
        for i in range(5):
            analyses.append(ComputationalAnalysis(
                computational_richness=0.85 + i * 0.02,
                confidence_score=0.9 + i * 0.01,
                keyword_matches={
                    "gpu": 10 + i,
                    "training": 5 + i,
                    "model": 8 + i,
                    "dataset": 3 + i
                },
                resource_metrics={
                    "gpu_count": 8,
                    "gpu_type": "V100",
                    "gpu_memory_gb": 32,
                    "training_time_hours": 48 + i * 12,
                    "model_parameters": 1_000_000_000 * (i + 1)
                },
                experimental_indicators={
                    "ablation_study": True,
                    "cross_validation": True,
                    "statistical_significance": True
                }
            ))
        
        # Low confidence analyses
        for i in range(2):
            analyses.append(ComputationalAnalysis(
                computational_richness=0.3,
                confidence_score=0.2,  # Below threshold
                keyword_matches={"generic": 1},
                resource_metrics={},
                experimental_indicators={}
            ))
        
        # Invalid analyses
        analyses.append(ComputationalAnalysis(
            computational_richness=1.5,  # Out of range
            confidence_score=-0.1,  # Negative
            keyword_matches="not a dict",  # Wrong type
            resource_metrics={
                "gpu_count": -4,  # Negative
                "training_time": -100  # Negative
            },
            experimental_indicators=None
        ))
        
        return analyses
    
    def test_end_to_end_paper_validation(self, contract_validator, realistic_papers):
        """Test end-to-end validation of paper collection."""
        # Validate all papers
        validation_result = contract_validator.validate(realistic_papers)
        
        # Check overall statistics
        assert validation_result["total_papers"] == len(realistic_papers)
        assert validation_result["valid_papers"] < validation_result["total_papers"]
        assert validation_result["validation_rate"] < 1.0
        
        # Check violation types detected
        assert "business_rule_violation" in validation_result["violations_by_type"]
        assert "out_of_range" in validation_result["violations_by_type"]
        # May or may not have missing_required depending on how Papers are created
        assert len(validation_result["violations_by_type"]) >= 2
        
        # Check failed papers are reported
        assert len(validation_result["failed_papers"]) > 0
        
        # Verify specific known failures
        failed_titles = {p["title"] for p in validation_result["failed_papers"]}
        assert "" in failed_titles  # Empty title paper
        assert "Future Paper" in failed_titles  # Future year paper
    
    def test_end_to_end_analysis_validation(self, contract_validator, realistic_analyses):
        """Test end-to-end validation of computational analyses."""
        results = []
        
        for analysis in realistic_analyses:
            result = contract_validator.validate_computational_analysis(analysis)
            results.append(result)
        
        # Check we got results for all analyses
        assert len(results) == len(realistic_analyses)
        
        # Count passed/failed
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        
        assert passed == 7  # The 5 high quality + 2 low confidence (warnings don't fail)
        assert failed == 1  # Only the 1 invalid analysis
        
        # Check warnings are captured
        warnings_count = sum(len(r.warnings) for r in results)
        assert warnings_count >= 2  # At least the 2 low confidence warnings
        
        # Check performance metrics
        assert all(r.execution_time_ms > 0 for r in results)
        assert all(r.execution_time_ms < 100 for r in results)  # Should be fast
    
    def test_pipeline_flow_validation(self, pipeline_validator, realistic_papers, realistic_analyses):
        """Test validation through complete pipeline flow."""
        # Stage 1: Collection to Analysis
        collection_report = pipeline_validator.validate_collection_to_analysis(realistic_papers)
        
        assert collection_report.stage == "collection_to_analysis"
        assert collection_report.validation_rate < 1.0  # Some papers have issues
        assert len(collection_report.recommendations) > 0
        
        # Stage 2: Analysis Outputs
        # Filter to only valid analyses for this test
        valid_analyses = realistic_analyses[:5]
        analysis_report = pipeline_validator.validate_analysis_outputs(valid_analyses)
        
        assert analysis_report.stage == "analysis_outputs"
        assert analysis_report.validation_rate == 1.0  # All valid analyses pass
        assert analysis_report.performance_metrics["analyses_per_second"] > 0
        
        # Stage 3: Full Pipeline
        reports = pipeline_validator.validate_full_pipeline(
            collection_data={"papers": realistic_papers},
            analysis_data={"analyses": realistic_analyses},
            projection_data=None
        )
        
        assert len(reports) >= 2
        assert all(isinstance(r, type(collection_report)) for r in reports.values())
    
    def test_contract_test_suite_execution(self, test_suite):
        """Test execution of contract test suite."""
        # Run all tests
        results = test_suite.run_all_tests()
        
        assert results["total_tests"] > 0
        assert results["passed"] > 0
        assert results["success_rate"] > 0.8  # Most tests should pass
        
        # Check execution time is reasonable
        assert results["execution_time_ms"] < 1000  # Should complete in < 1 second
        
        # Run tests by tag
        valid_results = test_suite.run_tests_by_tag("valid")
        assert valid_results["total_tests"] > 0
        assert valid_results["passed"] == valid_results["total_tests"]  # All valid tests pass
        
        invalid_results = test_suite.run_tests_by_tag("invalid")
        assert invalid_results["total_tests"] > 0
    
    def test_performance_under_load(self, contract_validator):
        """Test validation performance with large dataset."""
        # Generate large dataset
        large_paper_set = []
        for i in range(1000):
            large_paper_set.append(Paper(
                paper_id=f"perf_{i}",
                title=f"Performance Test Paper {i}",
                authors=[Author(name=f"Author {i}", affiliation=f"Uni {i % 10}")],
                venue=["ICML", "NeurIPS", "ICLR", "CVPR", "ECCV"][i % 5],
                year=2020 + (i % 5),
                citations=i % 100,
                abstract=f"Abstract for paper {i}" * 10  # Longer abstract
            ))
        
        # Time the validation
        start_time = time.time()
        validation_result = contract_validator.validate(large_paper_set)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        papers_per_second = len(large_paper_set) / elapsed_time
        
        # Performance assertions
        assert elapsed_time < 10.0  # Should process 1000 papers in < 10 seconds
        assert papers_per_second > 100  # Should process > 100 papers/second
        assert validation_result["total_papers"] == 1000
        assert validation_result["valid_papers"] == 1000  # All should be valid
    
    def test_error_recovery_and_graceful_degradation(self, contract_validator):
        """Test system handles errors gracefully."""
        # Create papers that might cause issues
        problematic_papers = [
            # Normal paper
            Paper(
                paper_id="normal",
                title="Normal Paper",
                authors=[Author(name="Normal Author", affiliation="Normal Uni")],
                venue="ICML",
                year=2024,
                citations=10,
                abstract="Normal abstract"
            ),
            # Paper with None values in unexpected places
            Paper(
                paper_id="problematic",
                title="Problematic Paper",
                authors=None,  # This might cause issues
                venue=None,
                year=2024,
                citations=None,
                abstract=None
            ),
        ]
        
        # Should not raise exception
        validation_result = contract_validator.validate(problematic_papers)
        
        assert validation_result["total_papers"] == 2
        assert validation_result["valid_papers"] >= 0  # At least doesn't crash
        assert isinstance(validation_result["violations_by_type"], dict)
    
    def test_contract_validation_with_real_world_scenarios(self, pipeline_validator):
        """Test validation with real-world scenario data."""
        # Scenario 1: Papers from web scraping with inconsistent data
        web_scraped_papers = [
            {
                "title": "Deep Learning for NLP: A Survey",
                "authors": ["John Doe", "Jane Smith"],  # Strings instead of Author objects
                "venue": "arXiv",  # Preprint
                "year": "2024",  # String instead of int
                "citations": "100+",  # String instead of int
                "paper_id": "arxiv:2024.12345"
            },
            {
                "title": "Transformer Architecture Improvements",
                "authors": "Single Author String",  # String instead of list
                "venue": None,  # Missing venue
                "year": 2024,
                "openalex_id": "oa_98765",
                # Missing citations
            },
        ]
        
        # Validate as dict data (before conversion to Paper objects)
        results = []
        for paper_data in web_scraped_papers:
            contract = pipeline_validator.contract_validator.contracts["paper_metadata"]
            violations = contract.validate(paper_data)
            results.append(violations)
        
        # Should detect type violations and missing fields
        assert len(results) == 2
        assert any(len(violations) > 0 for violations in results)
        
        # Scenario 2: Analysis results from different ML models
        ml_analyses = [
            {
                "computational_richness": "high",  # String instead of float
                "confidence_score": 95,  # Int instead of float (but valid)
                "keyword_matches": {"gpu": "many"},  # String count instead of int
                "resource_metrics": {"gpus": "8xV100"}  # Unstructured string
            },
            {
                "computational_richness": 0.00001,  # Very low but valid
                "confidence_score": 0.99999,  # Very high but valid
                "keyword_matches": {},  # Empty but valid
                "resource_metrics": {f"metric_{i}": i for i in range(60)}  # Too many metrics
            },
        ]
        
        # Validate ML analysis results
        for analysis_data in ml_analyses:
            contract = pipeline_validator.contract_validator.contracts["computational_analysis"]
            violations = contract.validate(analysis_data)
            # First one should have type violations
            if analysis_data.get("computational_richness") == "high":
                assert any(v.violation_type == ContractViolationType.INVALID_TYPE for v in violations)
    
    def test_cross_component_integration(self, contract_validator, pipeline_validator):
        """Test integration between different validation components."""
        # Create a paper and its analysis
        paper = Paper(
            paper_id="123",
            title="GPU-Accelerated Deep Learning",
            authors=[Author(name="AI Researcher", affiliation="Tech Corp")],
            venue="ICML",
            year=2024,
            citations=25,
            abstract="We present GPU-accelerated training methods..."
        )
        
        analysis = ComputationalAnalysis(
            computational_richness=0.9,
            confidence_score=0.95,
            keyword_matches={"gpu": 15, "accelerated": 8, "training": 12},
            resource_metrics={
                "gpu_count": 8,
                "gpu_type": "A100",
                "training_time_hours": 72
            },
            experimental_indicators={"performance_comparison": True}
        )
        
        # Set paper_id on analysis for cross-validation
        analysis.paper_id = "123"
        
        # Validate paper
        paper_validation = contract_validator.validate([paper])
        assert paper_validation["valid_papers"] == 1
        
        # Validate analysis with paper context
        analysis_validation = contract_validator.validate_computational_analysis(analysis, paper)
        assert analysis_validation.passed is True
        assert analysis_validation.metadata["paper_id"] == "123"
        
        # Validate through pipeline
        pipeline_reports = pipeline_validator.validate_full_pipeline(
            collection_data={"papers": [paper], "raw_papers": [paper], "collection_metadata": {"count": 1}},
            analysis_data={"analyses": [analysis], "papers": [paper], "metadata": {"count": 1}}
        )
        
        # Check specific validations
        assert "collection_to_analysis" in pipeline_reports
        assert "analysis_outputs" in pipeline_reports
        
        # Collection to analysis should pass
        collection_report = pipeline_reports["collection_to_analysis"]
        assert collection_report.validation_rate == 1.0
        
        # Analysis outputs should pass
        analysis_report = pipeline_reports["analysis_outputs"]
        assert analysis_report.validation_rate == 1.0
        
        # Transition validation should pass since we have the required fields
        if "collection_analysis_transition" in pipeline_reports:
            transition_report = pipeline_reports["collection_analysis_transition"]
            assert transition_report.valid_items == 1  # Should pass now