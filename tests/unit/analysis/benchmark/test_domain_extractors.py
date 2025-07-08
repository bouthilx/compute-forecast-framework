"""Tests for domain-specific benchmark extractors."""

import pytest

from compute_forecast.analysis.benchmark.domain_extractors import (
    NLPBenchmarkExtractor,
    CVBenchmarkExtractor,
    RLBenchmarkExtractor,
)
from compute_forecast.data.models import Paper, Author


class TestNLPBenchmarkExtractor:
    """Test NLP-specific extraction functionality."""

    @pytest.fixture
    def nlp_extractor(self):
        """Create an NLP benchmark extractor."""
        return NLPBenchmarkExtractor()

    @pytest.fixture
    def nlp_paper(self):
        """Create a sample NLP paper."""
        paper = Paper(
            paper_id="nlp_001",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            year=2019,
            venue="NAACL",
            authors=[Author(name="Devlin et al.")],
            citations=1000,
            abstract="We introduce BERT, trained on BookCorpus and Wikipedia.",
        )
        # Add full_text as an attribute
        paper.full_text = """
        Our model was pre-trained on 3.3 billion words from BookCorpus and Wikipedia.
        We used a vocabulary size of 30,522 WordPiece tokens.
        Maximum sequence length was set to 512 tokens.
        Pre-training took 4 days on 64 TPU chips.
        Fine-tuning on GLUE tasks took 1-3 hours on a single GPU.
        """
        return paper

    def test_nlp_benchmark_datasets(self, nlp_extractor):
        """Test NLP benchmark dataset list."""
        expected_datasets = ["GLUE", "SuperGLUE", "SQuAD", "WMT", "CommonCrawl"]
        assert all(ds in nlp_extractor.benchmark_datasets for ds in expected_datasets)

    def test_extract_nlp_specific_metrics(self, nlp_extractor, nlp_paper):
        """Test extracting NLP-specific metrics."""
        metrics = nlp_extractor.extract_nlp_specific_metrics(nlp_paper)

        assert "token_count" in metrics
        assert "vocabulary_size" in metrics
        assert "sequence_length" in metrics
        assert "pre_training" in metrics
        assert "fine_tuning" in metrics

        assert metrics["token_count"] == 3_300_000_000  # 3.3 billion
        assert metrics["vocabulary_size"] == 30522
        assert metrics["sequence_length"] == 512
        assert metrics["pre_training"] is True
        assert metrics["fine_tuning"] is True

    def test_normalize_nlp_metrics(self, nlp_extractor):
        """Test normalizing NLP metrics to standard units."""
        metrics = {
            "token_count": 1_000_000_000,  # 1B tokens
            "vocabulary_size": 50000,
            "sequence_length": 1024,
        }

        normalized = nlp_extractor.normalize_nlp_metrics(metrics)

        assert "word_count_estimate" in normalized
        assert normalized["word_count_estimate"] == pytest.approx(
            750_000_000, rel=0.1
        )  # ~0.75 words per token

    def test_extract_nlp_benchmarks_from_text(self, nlp_extractor, nlp_paper):
        """Test identifying NLP benchmark datasets in paper."""
        nlp_paper.full_text += """
        We evaluate on GLUE benchmark achieving 80.5% average score.
        On SuperGLUE, our model reaches 89.3%.
        SQuAD 2.0 F1 score: 93.2%
        """

        benchmarks = nlp_extractor.identify_benchmarks(nlp_paper)

        assert "GLUE" in benchmarks
        assert "SuperGLUE" in benchmarks
        assert "SQuAD" in benchmarks


class TestCVBenchmarkExtractor:
    """Test Computer Vision specific extraction functionality."""

    @pytest.fixture
    def cv_extractor(self):
        """Create a CV benchmark extractor."""
        return CVBenchmarkExtractor()

    @pytest.fixture
    def cv_paper(self):
        """Create a sample CV paper."""
        paper = Paper(
            paper_id="cv_001",
            title="EfficientNet: Rethinking Model Scaling",
            year=2019,
            venue="ICML",
            authors=[Author(name="Tan et al.")],
            citations=500,
            abstract="We systematically study model scaling for ConvNets.",
        )
        paper.full_text = """
        Training on ImageNet with resolution 224x224.
        Batch size 2048 across 64 TPU cores.
        Training throughput: 1200 images/second.
        Used RandAugment for data augmentation.
        Multi-scale training with resolutions from 224 to 380.
        Achieved 84.3% top-1 accuracy on ImageNet.
        MS-COCO detection mAP: 52.6%
        """
        return paper

    def test_cv_benchmark_datasets(self, cv_extractor):
        """Test CV benchmark dataset list."""
        expected_datasets = ["ImageNet", "COCO", "CIFAR", "ADE20K", "Kinetics"]
        assert all(ds in cv_extractor.benchmark_datasets for ds in expected_datasets)

    def test_extract_cv_specific_metrics(self, cv_extractor, cv_paper):
        """Test extracting CV-specific metrics."""
        metrics = cv_extractor.extract_cv_specific_metrics(cv_paper)

        assert "image_resolution" in metrics
        assert "throughput_fps" in metrics
        assert "augmentation_compute" in metrics
        assert "multi_scale_training" in metrics

        assert metrics["image_resolution"] == (224, 224)
        assert metrics["throughput_fps"] == 1200
        assert metrics["augmentation_compute"] is True
        assert metrics["multi_scale_training"] is True

    def test_extract_cv_benchmarks_from_text(self, cv_extractor, cv_paper):
        """Test identifying CV benchmark datasets in paper."""
        benchmarks = cv_extractor.identify_benchmarks(cv_paper)

        assert "ImageNet" in benchmarks
        assert "COCO" in benchmarks

    def test_calculate_cv_compute_overhead(self, cv_extractor):
        """Test calculating compute overhead for CV tasks."""
        metrics = {
            "image_resolution": (384, 384),
            "multi_scale_training": True,
            "augmentation_compute": True,
        }

        overhead = cv_extractor.calculate_compute_overhead(metrics)

        # Higher resolution and multi-scale should increase overhead
        assert overhead > 1.0
        assert overhead <= 3.0  # Reasonable upper bound


class TestRLBenchmarkExtractor:
    """Test Reinforcement Learning specific extraction functionality."""

    @pytest.fixture
    def rl_extractor(self):
        """Create an RL benchmark extractor."""
        return RLBenchmarkExtractor()

    @pytest.fixture
    def rl_paper(self):
        """Create a sample RL paper."""
        paper = Paper(
            paper_id="rl_001",
            title="Mastering Atari with Discrete World Models",
            year=2021,
            venue="ICLR",
            authors=[Author(name="Hafner et al.")],
            citations=200,
            abstract="We introduce DreamerV2, achieving human-level Atari performance.",
        )
        paper.full_text = """
        Trained on 57 Atari games for 200M environment steps each.
        Used 16 parallel environments for data collection.
        Total simulation time: 10 days on 1 GPU per game.
        Experience replay buffer size: 2M transitions.
        Achieved superhuman performance on 40 games.
        MuJoCo continuous control: 1000+ reward on Humanoid-v2.
        """
        return paper

    def test_rl_benchmark_environments(self, rl_extractor):
        """Test RL benchmark environment list."""
        expected_envs = ["Atari", "MuJoCo", "OpenAI Gym", "StarCraft", "Dota"]
        assert all(env in rl_extractor.benchmark_environments for env in expected_envs)

    def test_extract_rl_specific_metrics(self, rl_extractor, rl_paper):
        """Test extracting RL-specific metrics."""
        metrics = rl_extractor.extract_rl_specific_metrics(rl_paper)

        assert "environment_steps" in metrics
        assert "simulation_time_days" in metrics
        assert "parallel_environments" in metrics
        assert "experience_replay_size" in metrics

        assert metrics["environment_steps"] == 200_000_000  # 200M
        assert metrics["simulation_time_days"] == 10
        assert metrics["parallel_environments"] == 16
        assert metrics["experience_replay_size"] == 2_000_000

    def test_extract_rl_benchmarks_from_text(self, rl_extractor, rl_paper):
        """Test identifying RL benchmark environments in paper."""
        benchmarks = rl_extractor.identify_benchmarks(rl_paper)

        assert "Atari" in benchmarks
        assert "MuJoCo" in benchmarks

    def test_calculate_rl_compute_requirements(self, rl_extractor):
        """Test calculating total compute for RL training."""
        metrics = {
            "environment_steps": 1_000_000_000,  # 1B steps
            "parallel_environments": 32,
            "simulation_time_days": 14,
        }

        compute_estimate = rl_extractor.estimate_compute_hours(metrics)

        assert compute_estimate > 0
        assert compute_estimate == pytest.approx(
            14 * 24 * 32, rel=0.1
        )  # ~10752 GPU hours (14 days × 24 hours × 32 envs)

    def test_extract_multiple_rl_environments(self, rl_extractor):
        """Test extracting metrics when multiple RL environments are used."""
        paper = Paper(
            paper_id="rl_multi",
            title="Multi-Environment RL Agent",
            year=2022,
            venue="NeurIPS",
            authors=[Author(name="Researcher")],
            citations=50,
            abstract="Multi-environment reinforcement learning agent.",
        )
        paper.full_text = """
        Evaluated on Atari-57 with 100M steps per game.
        Also tested on MuJoCo tasks: Ant, Humanoid, Hopper.
        OpenAI Gym CartPole solved in 200 episodes.
        Total training: 500 GPU hours across all environments.
        """

        benchmarks = rl_extractor.identify_benchmarks(paper)
        rl_extractor.extract_rl_specific_metrics(paper)

        assert len(benchmarks) >= 3
        assert "Atari" in benchmarks
        assert "MuJoCo" in benchmarks
        assert "OpenAI Gym" in benchmarks
