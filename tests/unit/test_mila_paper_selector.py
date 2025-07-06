"""Tests for Mila paper selection and filtering."""

import pytest

from compute_forecast.analysis.mila.paper_selector import (
    MilaPaperSelector,
    PaperSelectionCriteria,
    DomainClassifier,
    ComputationalContentFilter,
)


class TestPaperSelectionCriteria:
    """Test paper selection criteria validation."""

    def test_default_criteria(self):
        """Test default selection criteria."""
        criteria = PaperSelectionCriteria()
        assert criteria.start_year == 2019
        assert criteria.end_year == 2024
        assert criteria.papers_per_year_min == 15
        assert criteria.papers_per_year_max == 30
        assert criteria.papers_per_domain_per_year_min == 5
        assert criteria.papers_per_domain_per_year_max == 10
        assert criteria.domains == ["NLP", "CV", "RL"]
        assert criteria.min_computational_richness == 0.4

    def test_custom_criteria(self):
        """Test custom selection criteria."""
        criteria = PaperSelectionCriteria(
            start_year=2020,
            end_year=2023,
            papers_per_year_min=10,
            papers_per_year_max=20,
        )
        assert criteria.start_year == 2020
        assert criteria.end_year == 2023
        assert criteria.papers_per_year_min == 10
        assert criteria.papers_per_year_max == 20


class TestDomainClassifier:
    """Test domain classification for papers."""

    @pytest.fixture
    def classifier(self):
        return DomainClassifier()

    def test_classify_nlp_paper(self, classifier):
        """Test NLP paper classification."""
        paper = {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "abstract": "We introduce a new language representation model called BERT",
        }
        assert classifier.classify(paper) == "NLP"

    def test_classify_cv_paper(self, classifier):
        """Test computer vision paper classification."""
        paper = {
            "title": "Deep Residual Learning for Image Recognition",
            "abstract": "Deeper neural networks for image classification using residual connections",
        }
        assert classifier.classify(paper) == "CV"

    def test_classify_rl_paper(self, classifier):
        """Test reinforcement learning paper classification."""
        paper = {
            "title": "Mastering the game of Go with deep neural networks",
            "abstract": "We train a reinforcement learning agent using Monte Carlo tree search",
        }
        assert classifier.classify(paper) == "RL"

    def test_classify_multi_domain_paper(self, classifier):
        """Test paper with multiple domain indicators."""
        paper = {
            "title": "Vision-Language Pre-training for Multimodal Tasks",
            "abstract": "Combining vision transformers with language models for image captioning",
        }
        # Should return primary domain
        domain = classifier.classify(paper)
        assert domain in ["NLP", "CV"]

    def test_classify_unknown_paper(self, classifier):
        """Test paper with no clear domain."""
        paper = {
            "title": "A Study on Software Engineering Practices",
            "abstract": "We analyze software development methodologies",
        }
        assert classifier.classify(paper) == "Other"


class TestComputationalContentFilter:
    """Test computational content filtering."""

    @pytest.fixture
    def filter(self):
        return ComputationalContentFilter()

    def test_high_computational_content(self, filter):
        """Test paper with high computational content."""
        paper = {
            "title": "Training Large Language Models at Scale",
            "abstract": "We trained a 175B parameter model on 8192 A100 GPUs for 3 months",
        }
        score = filter.compute_richness_score(paper)
        assert score >= 0.7  # High computational content

    def test_medium_computational_content(self, filter):
        """Test paper with medium computational content."""
        paper = {
            "title": "Fine-tuning BERT for Text Classification",
            "abstract": "We fine-tuned BERT on 4 V100 GPUs for downstream tasks",
        }
        score = filter.compute_richness_score(paper)
        assert 0.4 <= score <= 0.8

    def test_low_computational_content(self, filter):
        """Test paper with low computational content."""
        paper = {
            "title": "A Survey of Deep Learning Methods",
            "abstract": "We review recent advances in deep learning architectures",
        }
        score = filter.compute_richness_score(paper)
        assert score < 0.4

    def test_filter_papers_by_richness(self, filter):
        """Test filtering papers by computational richness."""
        papers = [
            {"title": "Training GPT-3", "abstract": "175B parameters, 10000 GPU hours"},
            {"title": "Survey of NLP", "abstract": "Review of methods"},
            {"title": "BERT fine-tuning", "abstract": "4 GPUs, 24 hours training"},
        ]
        filtered = filter.filter_by_richness(papers, min_score=0.4)
        assert len(filtered) == 2
        assert filtered[0]["title"] == "Training GPT-3"
        assert filtered[1]["title"] == "BERT fine-tuning"


class TestMilaPaperSelector:
    """Test Mila paper selection pipeline."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            {
                "paper_id": "1",
                "title": "Scaling Laws for Neural Language Models",
                "abstract": "We train language models from 768M to 1.5B parameters on V100 GPUs",
                "authors": [
                    {"author": {"name": "John Doe", "links": [{"type": "email.mila"}]}}
                ],
                "releases": [{"venue": {"date": {"text": "2020-06-01"}}}],
            },
            {
                "paper_id": "2",
                "title": "Vision Transformer for Image Classification",
                "abstract": "ViT trained on ImageNet using 16 TPU v3 cores for 2 weeks",
                "authors": [
                    {
                        "author": {
                            "name": "Jane Smith",
                            "links": [{"type": "email.mila"}],
                        }
                    }
                ],
                "releases": [{"venue": {"date": {"text": "2020-10-01"}}}],
            },
            {
                "paper_id": "3",
                "title": "Deep Q-Learning for Atari Games",
                "abstract": "DQN agent trained on 8 GPUs for 50M frames",
                "authors": [
                    {
                        "author": {
                            "name": "Bob Johnson",
                            "links": [{"type": "email.mila"}],
                        }
                    }
                ],
                "releases": [{"venue": {"date": {"text": "2021-03-15"}}}],
            },
            {
                "paper_id": "4",
                "title": "Survey of Transformer Architectures",
                "abstract": "We review recent transformer variants",
                "authors": [
                    {
                        "author": {
                            "name": "Alice Brown",
                            "links": [{"type": "email.mila"}],
                        }
                    }
                ],
                "releases": [{"venue": {"date": {"text": "2021-07-01"}}}],
            },
        ]

    @pytest.fixture
    def selector(self):
        return MilaPaperSelector()

    def test_load_papers_from_file(self, selector, tmp_path):
        """Test loading papers from JSON file."""
        import json

        test_file = tmp_path / "test_papers.json"
        papers = [{"paper_id": "1", "title": "Test Paper"}]
        test_file.write_text(json.dumps(papers))

        loaded_papers = selector.load_papers(str(test_file))
        assert len(loaded_papers) == 1
        assert loaded_papers[0]["title"] == "Test Paper"

    def test_filter_by_year(self, selector, sample_papers):
        """Test filtering papers by year range."""
        filtered = selector.filter_by_year(sample_papers, 2020, 2021)
        assert len(filtered) == 4  # All sample papers are in range

        filtered = selector.filter_by_year(sample_papers, 2021, 2021)
        assert len(filtered) == 2
        assert all(
            "2021" in p["releases"][0]["venue"]["date"]["text"] for p in filtered
        )

    def test_select_papers_balanced(self, selector, sample_papers):
        """Test balanced paper selection across domains."""
        criteria = PaperSelectionCriteria(
            start_year=2020,
            end_year=2021,
            papers_per_year_min=2,
            papers_per_year_max=3,
            papers_per_domain_per_year_min=1,
            papers_per_domain_per_year_max=1,
        )

        selected = selector.select_papers(sample_papers, criteria)

        # Check that we selected some papers
        assert len(selected) >= 3  # We have 3 papers with good computational content

        # Check year distribution - should have papers from both years
        years = set()
        for paper in selected:
            year = int(paper["releases"][0]["venue"]["date"]["text"][:4])
            years.add(year)

        # Should have papers from both 2020 and 2021
        assert 2020 in years
        assert 2021 in years

    def test_select_papers_with_venues(self, selector):
        """Test paper selection considers venue quality."""
        papers = [
            {
                "paper_id": "1",
                "title": "NLP Paper at NeurIPS",
                "abstract": "Transformer model trained on 100 GPUs",
                "releases": [{"venue": {"name": "NeurIPS", "date": {"text": "2020"}}}],
                "authors": [{"author": {"links": [{"type": "email.mila"}]}}],
            },
            {
                "paper_id": "2",
                "title": "NLP Paper at Workshop",
                "abstract": "Small model experiments",
                "releases": [{"venue": {"name": "Workshop", "date": {"text": "2020"}}}],
                "authors": [{"author": {"links": [{"type": "email.mila"}]}}],
            },
        ]

        selected = selector.select_papers(papers, PaperSelectionCriteria())
        # Should prefer top-tier venue paper
        assert any(p["paper_id"] == "1" for p in selected)

    def test_export_selection_summary(self, selector, sample_papers):
        """Test export of selection summary."""
        criteria = PaperSelectionCriteria()
        selected = selector.select_papers(sample_papers, criteria)

        summary = selector.generate_selection_summary(selected)

        assert "total_selected" in summary
        assert "by_year" in summary
        assert "by_domain" in summary
        assert "computational_richness" in summary

        # Check structure
        assert isinstance(summary["by_year"], dict)
        assert isinstance(summary["by_domain"], dict)
        assert "mean" in summary["computational_richness"]
        assert "std" in summary["computational_richness"]
