"""Tests for extraction templates with suppression indicators."""

import pytest
from typing import Dict, List

from src.extraction.suppression_templates import (
    SuppressionTemplates,
    SuppressionField,
    SuppressionIndicators,
    SuppressionTemplate
)


class TestSuppressionField:
    """Test suppression field enumeration."""
    
    def test_suppression_fields_exist(self):
        """Test all suppression fields are defined."""
        assert SuppressionField.NUM_ABLATIONS
        assert SuppressionField.NUM_SEEDS
        assert SuppressionField.NUM_BASELINES
        assert SuppressionField.NUM_MODEL_VARIANTS
        assert SuppressionField.MISSING_EXPERIMENTS
        assert SuppressionField.MODEL_SIZE_PERCENTILE
        assert SuppressionField.TRAINING_TRUNCATED
        assert SuppressionField.DATASET_SUBSAMPLED
        assert SuppressionField.EFFICIENCY_FOCUSED
        assert SuppressionField.COMPUTE_SAVING_TECHNIQUES
        assert SuppressionField.CONSTRAINTS_MENTIONED
        assert SuppressionField.CONSTRAINT_QUOTES


class TestSuppressionIndicators:
    """Test suppression indicators structure."""
    
    def test_experimental_scope_indicators(self):
        """Test experimental scope fields."""
        indicators = SuppressionIndicators()
        scope = indicators.experimental_scope
        
        assert scope["num_ablations"] is None
        assert scope["num_seeds"] is None
        assert scope["num_baselines"] is None
        assert scope["num_model_variants"] is None
        assert scope["standard_experiments_missing"] == []
    
    def test_scale_analysis_indicators(self):
        """Test scale analysis fields."""
        indicators = SuppressionIndicators()
        scale = indicators.scale_analysis
        
        assert scale["parameter_percentile"] is None
        assert scale["training_duration"] is None
        assert scale["dataset_usage"] is None
        assert scale["convergence_achieved"] is None
    
    def test_method_classification_indicators(self):
        """Test method classification fields."""
        indicators = SuppressionIndicators()
        method = indicators.method_classification
        
        assert method["efficiency_focused"] is False
        assert method["compute_saving_techniques"] == []
        assert method["method_type"] is None
    
    def test_explicit_constraints_indicators(self):
        """Test explicit constraints fields."""
        indicators = SuppressionIndicators()
        constraints = indicators.explicit_constraints
        
        assert constraints["mentions_constraints"] is False
        assert constraints["constraint_quotes"] == []
        assert constraints["workarounds_described"] == []


class TestSuppressionTemplates:
    """Test suppression extraction templates."""
    
    def test_nlp_with_suppression_template(self):
        """Test NLP template with suppression indicators."""
        template = SuppressionTemplates.nlp_with_suppression()
        
        # Check basic info
        assert template.template_id == "nlp_training_suppression_v1"
        assert "Suppression" in template.template_name
        
        # Check suppression fields are included
        assert SuppressionField.NUM_ABLATIONS in template.suppression_fields
        assert SuppressionField.NUM_SEEDS in template.suppression_fields
        assert SuppressionField.EFFICIENCY_FOCUSED in template.suppression_fields
        
        # Check extraction patterns exist
        assert len(template.suppression_patterns) > 0
        assert "ablation_count" in template.suppression_patterns
        assert "seed_count" in template.suppression_patterns
        assert "constraint_mentions" in template.suppression_patterns
    
    def test_cv_with_suppression_template(self):
        """Test CV template with suppression indicators."""
        template = SuppressionTemplates.cv_with_suppression()
        
        assert template.template_id == "cv_training_suppression_v1"
        assert "Suppression" in template.template_name
        
        # CV-specific suppression fields
        assert SuppressionField.NUM_MODEL_VARIANTS in template.suppression_fields
        assert SuppressionField.DATASET_SUBSAMPLED in template.suppression_fields
    
    def test_rl_with_suppression_template(self):
        """Test RL template with suppression indicators."""
        template = SuppressionTemplates.rl_with_suppression()
        
        assert template.template_id == "rl_training_suppression_v1"
        assert "Suppression" in template.template_name
        
        # RL-specific suppression fields
        assert SuppressionField.NUM_SEEDS in template.suppression_fields
        assert SuppressionField.TRAINING_TRUNCATED in template.suppression_fields
    
    def test_suppression_patterns(self):
        """Test extraction patterns for suppression indicators."""
        template = SuppressionTemplates.nlp_with_suppression()
        patterns = template.suppression_patterns
        
        # Test ablation patterns
        assert "ablation_count" in patterns
        ablation_pattern = patterns["ablation_count"]
        test_text = "We conduct 3 ablation studies to analyze"
        assert ablation_pattern.search(test_text) is not None
        
        # Test seed patterns
        assert "seed_count" in patterns
        seed_pattern = patterns["seed_count"]
        test_text = "Results averaged over 5 random seeds"
        assert seed_pattern.search(test_text) is not None
        
        # Test constraint patterns
        assert "constraint_mentions" in patterns
        constraint_pattern = patterns["constraint_mentions"]
        test_text = "Due to computational constraints, we limit"
        assert constraint_pattern.search(test_text) is not None
    
    def test_extract_suppression_indicators(self):
        """Test extraction of suppression indicators from text."""
        template = SuppressionTemplates.nlp_with_suppression()
        
        paper_text = """
        We train BERT on 4 V100 GPUs for 24 hours. Due to computational constraints,
        we only conduct 2 ablation studies instead of the typical 5. Results are
        averaged over 3 random seeds. We use knowledge distillation to reduce
        model size from 110M to 66M parameters. Training was stopped early at
        80% of convergence due to resource limits.
        """
        
        indicators = template.extract_suppression_indicators(paper_text)
        
        assert indicators.experimental_scope["num_ablations"] == 2
        assert indicators.experimental_scope["num_seeds"] == 3
        assert indicators.explicit_constraints["mentions_constraints"] is True
        assert indicators.method_classification["efficiency_focused"] is True
        techniques = indicators.method_classification["compute_saving_techniques"]
        assert any("distillation" in technique for technique in techniques)
    
    def test_calculate_suppression_score(self):
        """Test calculation of overall suppression score."""
        indicators = SuppressionIndicators()
        
        # Low suppression (good resources)
        indicators.experimental_scope["num_ablations"] = 5
        indicators.experimental_scope["num_seeds"] = 10
        indicators.scale_analysis["parameter_percentile"] = 75
        
        score = SuppressionTemplates.calculate_suppression_score(indicators)
        assert score < 0.3  # Low suppression
        
        # High suppression (limited resources)
        indicators.experimental_scope["num_ablations"] = 1
        indicators.experimental_scope["num_seeds"] = 1
        indicators.scale_analysis["parameter_percentile"] = 15
        indicators.explicit_constraints["mentions_constraints"] = True
        
        score = SuppressionTemplates.calculate_suppression_score(indicators)
        assert score > 0.7  # High suppression