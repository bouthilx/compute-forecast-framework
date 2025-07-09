"""Mock data generators for testing."""

import random
from datetime import datetime
from typing import List

from compute_forecast.data.models import (
    Author,
    AuthorshipAnalysis,
    ComputationalAnalysis,
    Paper,
    VenueAnalysis,
)
from compute_forecast.testing.mock_data.configs import DataQuality, MockDataConfig


class MockDataGenerator:
    """Generator for creating realistic mock paper data."""

    # Realistic venue names from ML/AI conferences
    VENUES = [
        "NeurIPS",
        "ICML",
        "ICLR",
        "CVPR",
        "ICCV",
        "ECCV",
        "ACL",
        "EMNLP",
        "AAAI",
        "IJCAI",
        "KDD",
        "SIGIR",
        "WSDM",
        "WWW",
        "COLT",
        "UAI",
        "AISTATS",
        "ICRA",
        "IROS",
        "CoRL",
        "SIGGRAPH",
        "SIGGRAPH Asia",
        "MICCAI",
        "IPMI",
        "ISBI",
        "MIDL",
        "Nature",
        "Science",
        "PNAS",
        "Nature Machine Intelligence",
        "Science Robotics",
        "Cell",
        "arXiv",
        "Workshop on ML",
        "Symposium on AI",
        "Conference on DL",
    ]

    # Common first and last names for author generation
    FIRST_NAMES = [
        "John",
        "Jane",
        "Michael",
        "Maria",
        "David",
        "Sarah",
        "Robert",
        "Lisa",
        "James",
        "Patricia",
        "William",
        "Jennifer",
        "Richard",
        "Linda",
        "Thomas",
        "Barbara",
        "Charles",
        "Elizabeth",
        "Joseph",
        "Susan",
        "Christopher",
        "Jessica",
        "Daniel",
        "Karen",
        "Matthew",
        "Nancy",
        "Anthony",
        "Betty",
        "Mark",
        "Helen",
        "Paul",
        "Sandra",
        "Steven",
        "Donna",
        "Andrew",
        "Carol",
        "Kenneth",
        "Ruth",
        "Joshua",
        "Sharon",
        "Kevin",
        "Michelle",
        "Brian",
        "Laura",
        "George",
        "Amy",
    ]

    LAST_NAMES = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
        "Hernandez",
        "Lopez",
        "Gonzalez",
        "Wilson",
        "Anderson",
        "Thomas",
        "Taylor",
        "Moore",
        "Jackson",
        "Martin",
        "Lee",
        "Perez",
        "Thompson",
        "White",
        "Harris",
        "Sanchez",
        "Clark",
        "Ramirez",
        "Lewis",
        "Robinson",
        "Walker",
        "Young",
        "Allen",
        "King",
        "Wright",
        "Scott",
        "Torres",
        "Nguyen",
        "Hill",
        "Flores",
        "Green",
        "Adams",
        "Nelson",
        "Baker",
        "Hall",
        "Rivera",
        "Campbell",
        "Mitchell",
    ]

    # Academic and industry affiliations
    ACADEMIC_AFFILIATIONS = [
        "MIT",
        "Stanford University",
        "UC Berkeley",
        "Carnegie Mellon University",
        "University of Toronto",
        "Oxford University",
        "Cambridge University",
        "ETH Zurich",
        "EPFL",
        "University of Washington",
        "Georgia Tech",
        "Cornell University",
        "Princeton University",
        "Harvard University",
        "Yale University",
        "Columbia University",
        "NYU",
        "UCLA",
        "UCSD",
        "University of Michigan",
        "University of Illinois",
        "UT Austin",
        "University of Wisconsin",
        "University of Maryland",
        "Johns Hopkins",
        "Caltech",
        "University of Pennsylvania",
        "Duke University",
        "Northwestern",
    ]

    INDUSTRY_AFFILIATIONS = [
        "Google Research",
        "DeepMind",
        "OpenAI",
        "Microsoft Research",
        "Meta AI",
        "Apple ML Research",
        "Amazon Science",
        "NVIDIA Research",
        "IBM Research",
        "Adobe Research",
        "Salesforce Research",
        "Uber AI Labs",
        "Twitter Cortex",
        "Baidu Research",
        "Alibaba DAMO",
        "Tencent AI Lab",
        "Huawei Research",
        "Samsung Research",
        "Intel Labs",
        "Qualcomm AI Research",
        "ARM Research",
        "Tesla AI",
        "Anthropic",
        "Cohere",
        "Stability AI",
        "Midjourney",
    ]

    # Keywords for paper generation
    KEYWORDS = [
        "neural networks",
        "deep learning",
        "machine learning",
        "artificial intelligence",
        "computer vision",
        "natural language processing",
        "reinforcement learning",
        "transformer",
        "attention mechanism",
        "convolutional neural network",
        "recurrent neural network",
        "generative adversarial network",
        "autoencoder",
        "optimization",
        "gradient descent",
        "backpropagation",
        "regularization",
        "transfer learning",
        "few-shot learning",
        "meta-learning",
        "continual learning",
        "federated learning",
        "self-supervised learning",
        "unsupervised learning",
        "representation learning",
        "graph neural networks",
        "explainable AI",
        "fairness",
        "robustness",
        "interpretability",
        "causality",
        "uncertainty",
    ]

    # GPU types for computational analysis
    GPU_TYPES = [
        "NVIDIA V100",
        "NVIDIA A100",
        "NVIDIA A6000",
        "NVIDIA RTX 3090",
        "NVIDIA RTX 4090",
        "NVIDIA H100",
        "NVIDIA T4",
        "NVIDIA P100",
        "TPU v3",
        "TPU v4",
        "AMD MI250X",
        "AMD MI100",
    ]

    def __init__(self):
        """Initialize the generator."""
        self.random = None

    def generate(self, config: MockDataConfig) -> List[Paper]:
        """Generate mock papers based on configuration."""
        # Initialize random generator with seed for reproducibility
        self.random = random.Random(config.seed)

        papers = []
        for i in range(config.size):
            paper = self._generate_single_paper(i, config.quality)
            papers.append(paper)

        return papers

    def validate_output(self, papers: List[Paper], config: MockDataConfig) -> bool:
        """Validate that generated papers meet quality requirements."""
        if len(papers) != config.size:
            return False

        if config.quality == DataQuality.NORMAL:
            # Check essential fields for all papers
            for paper in papers:
                required_fields = [
                    paper.paper_id,
                    paper.title,
                    paper.authors,
                    paper.year,
                    paper.venue,
                    paper.abstract,
                ]
                if not all(required_fields):
                    return False

            # Check overall field population rate across all papers
            total_field_checks = 0
            populated_field_checks = 0

            for paper in papers:
                for field_name in [
                    "abstract",
                    "keywords",
                    "arxiv_id",
                    "openalex_id",
                    "computational_analysis",
                    "citation_velocity",
                ]:
                    total_field_checks += 1
                    value = getattr(paper, field_name, None)
                    if value is not None and (
                        not isinstance(value, list) or len(value) > 0
                    ):
                        populated_field_checks += 1

            # Overall population rate should be ~95% (allow 85% for margin)
            if populated_field_checks / total_field_checks < 0.85:
                return False

        elif config.quality == DataQuality.CORRUPTED:
            # For corrupted, check overall that many fields are missing
            total_optional_fields = 0
            populated_optional_fields = 0

            for paper in papers:
                for field_name in [
                    "abstract",
                    "keywords",
                    "arxiv_id",
                    "openalex_id",
                    "computational_analysis",
                ]:
                    total_optional_fields += 1
                    value = getattr(paper, field_name, None)
                    if value is not None and (
                        not isinstance(value, list) or len(value) > 0
                    ):
                        populated_optional_fields += 1

            # For corrupted, should have low population rate (~30%)
            if populated_optional_fields / total_optional_fields > 0.4:
                return False

        return True

    def _generate_single_paper(self, index: int, quality: DataQuality) -> Paper:
        """Generate a single paper with specified quality."""
        # Always generate essential fields
        # Use index and random for deterministic ID generation
        paper_id = f"paper_{self.random.randint(100000000000, 999999999999):x}"
        title = self._generate_title()
        authors = self._generate_authors(quality)
        year = self._generate_year()
        venue = self.random.choice(self.VENUES)
        citations = self._generate_citations(year)

        # Initialize optional fields
        abstract = None
        keywords = None
        arxiv_id = None
        openalex_id = None
        computational_analysis = None
        citation_velocity = None
        authorship_analysis = None
        venue_analysis = None

        # Populate fields based on quality
        if quality == DataQuality.NORMAL:
            # 95% field population
            abstract = self._generate_abstract()
            keywords = self._generate_keywords()
            if self.random.random() < 0.95:
                arxiv_id = f"{year}.{self.random.randint(10000, 99999)}"
            if self.random.random() < 0.95:
                openalex_id = f"W{self.random.randint(1000000000, 9999999999)}"
            if self.random.random() < 0.95:  # Increase to 95% for normal quality
                computational_analysis = self._generate_computational_analysis()
            if self.random.random() < 0.95:
                citation_velocity = self.random.uniform(0.1, 5.0)
            # Add authorship and venue analysis for some papers
            if self.random.random() < 0.8:
                authorship_analysis = self._generate_authorship_analysis(authors)
            if self.random.random() < 0.8:
                venue_analysis = self._generate_venue_analysis(venue)

        elif quality == DataQuality.EDGE_CASE:
            # 70% field population with unusual values
            if self.random.random() < 0.7:
                abstract = (
                    self._generate_abstract() if self.random.random() < 0.5 else ""
                )
            if self.random.random() < 0.7:
                keywords = (
                    self._generate_keywords() if self.random.random() < 0.5 else []
                )
            if self.random.random() < 0.5:
                arxiv_id = f"{year}.{self.random.randint(10000, 99999)}"
            if self.random.random() < 0.5:
                openalex_id = f"W{self.random.randint(1000000000, 9999999999)}"
            if self.random.random() < 0.3:
                computational_analysis = self._generate_computational_analysis()
            # Edge case: very high or very low citation velocity
            if self.random.random() < 0.5:
                citation_velocity = self.random.choice([0.0, 0.01, 50.0, 100.0])

        elif quality == DataQuality.CORRUPTED:
            # 30% field population
            if self.random.random() < 0.3:
                abstract = self._generate_abstract()[:50]  # Truncated
            if self.random.random() < 0.1:
                keywords = [self.random.choice(self.KEYWORDS)]
            # Most optional fields missing

        return Paper(
            paper_id=paper_id,
            title=title,
            authors=authors,
            venue=venue,
            year=year,
            citations=citations,
            abstract=abstract or "",
            keywords=keywords or [],
            arxiv_id=arxiv_id,
            openalex_id=openalex_id,
            computational_analysis=computational_analysis,
            citation_velocity=citation_velocity,
            normalized_venue=venue.lower().replace(" ", "_"),
            collection_source="mock_generator",
            collection_timestamp=datetime.now(),
            authorship_analysis=authorship_analysis,
            venue_analysis=venue_analysis,
        )

    def _generate_title(self) -> str:
        """Generate a realistic paper title."""
        templates = [
            "Learning {concept} for {task} using {method}",
            "Efficient {method} for Large-Scale {task}",
            "Towards Better {concept} in {domain}",
            "{method}: A Novel Approach to {task}",
            "Understanding {concept} through {method}",
            "Scaling {method} to {scale} {task}",
            "On the {property} of {method} in {domain}",
            "Improving {task} with {method} and {technique}",
            "{method} Meets {other_method}: {task} at Scale",
            "Rethinking {concept} for Modern {domain}",
        ]

        concepts = [
            "Representations",
            "Embeddings",
            "Architectures",
            "Optimization",
            "Generalization",
        ]
        tasks = [
            "Image Classification",
            "Object Detection",
            "Language Modeling",
            "Machine Translation",
            "Question Answering",
        ]
        methods = [
            "Transformers",
            "Graph Neural Networks",
            "Diffusion Models",
            "Contrastive Learning",
            "Meta-Learning",
        ]
        domains = [
            "Computer Vision",
            "Natural Language Processing",
            "Reinforcement Learning",
            "Medical Imaging",
            "Robotics",
        ]
        properties = [
            "Robustness",
            "Efficiency",
            "Interpretability",
            "Fairness",
            "Scalability",
        ]
        techniques = [
            "Data Augmentation",
            "Regularization",
            "Attention Mechanisms",
            "Knowledge Distillation",
            "Self-Supervision",
        ]
        scales = ["Million", "Billion", "Web-Scale", "Real-World", "Multi-Modal"]

        template = self.random.choice(templates)
        title = template.format(
            concept=self.random.choice(concepts),
            task=self.random.choice(tasks),
            method=self.random.choice(methods),
            domain=self.random.choice(domains),
            property=self.random.choice(properties),
            technique=self.random.choice(techniques),
            scale=self.random.choice(scales),
            other_method=self.random.choice(methods),
        )

        return str(title)

    def _generate_authors(self, quality: DataQuality) -> List[Author]:
        """Generate list of authors."""
        # Number of authors varies by quality
        if quality == DataQuality.NORMAL:
            num_authors = self.random.choices(
                [1, 2, 3, 4, 5, 6, 7], weights=[5, 20, 30, 25, 10, 5, 5]
            )[0]
        elif quality == DataQuality.EDGE_CASE:
            # Edge cases: single author or many authors
            num_authors = self.random.choices(
                [1, 10, 15, 20], weights=[30, 30, 20, 20]
            )[0]
        else:  # CORRUPTED
            num_authors = self.random.choices([0, 1, 2], weights=[10, 60, 30])[0]

        authors = []
        for i in range(num_authors):
            first_name = self.random.choice(self.FIRST_NAMES)
            last_name = self.random.choice(self.LAST_NAMES)
            name = f"{first_name} {last_name}"

            # Affiliation assignment
            affiliation = None
            if quality == DataQuality.NORMAL and self.random.random() < 0.9:
                # Mix of academic and industry
                if self.random.random() < 0.7:
                    affiliation = self.random.choice(self.ACADEMIC_AFFILIATIONS)
                else:
                    affiliation = self.random.choice(self.INDUSTRY_AFFILIATIONS)
            elif quality == DataQuality.EDGE_CASE and self.random.random() < 0.5:
                affiliation = self.random.choice(
                    self.ACADEMIC_AFFILIATIONS + self.INDUSTRY_AFFILIATIONS
                )

            # Email generation
            email = None
            if affiliation and self.random.random() < 0.3:
                email_user = f"{first_name.lower()}.{last_name.lower()}"
                domain = (
                    affiliation.lower().replace(" ", "").replace("university", "edu")
                )
                email = f"{email_user}@{domain}.com"

            authors.append(
                Author(
                    name=name,
                    affiliation=affiliation or "",
                    author_id=f"author_{self.random.randint(10000000, 99999999):x}",
                    email=email or "",
                )
            )

        return authors

    def _generate_year(self) -> int:
        """Generate publication year with realistic distribution."""
        # More recent years have higher probability
        years = list(range(2019, 2025))
        weights = [1, 2, 3, 5, 8, 13]  # Fibonacci-like growth for recency
        return int(self.random.choices(years, weights=weights)[0])

    def _generate_citations(self, year: int) -> int:
        """Generate citation count based on year and realistic distribution."""
        years_old = 2024 - year

        # Base citation distribution (power law)
        if years_old == 0:
            # Very recent papers have few citations
            base_citations = self.random.choices(
                [0, 1, 2, 3, 5, 10], weights=[40, 30, 15, 10, 4, 1]
            )[0]
        else:
            # Older papers follow power law distribution
            base_range = int(10 * years_old)
            if self.random.random() < 0.7:  # Most papers have few citations
                base_citations = self.random.randint(0, base_range)
            elif self.random.random() < 0.95:  # Some have moderate citations
                base_citations = self.random.randint(base_range, base_range * 5)
            else:  # Few have many citations
                base_citations = self.random.randint(base_range * 5, base_range * 50)

        return int(base_citations)

    def _generate_abstract(self) -> str:
        """Generate a realistic abstract."""
        intro_templates = [
            "We present a novel approach to {task} that leverages {method}.",
            "This paper introduces {method} for improving {task} performance.",
            "We propose a new framework for {task} based on {concept}.",
            "In this work, we address the challenge of {task} using {method}.",
        ]

        method_templates = [
            "Our approach combines {technique1} with {technique2} to achieve {benefit}.",
            "The key innovation is the use of {technique1} that enables {benefit}.",
            "We develop a {adjective} algorithm that {action} {target}.",
            "Our method employs {technique1} to {action} {challenge}.",
        ]

        result_templates = [
            "Experiments on {dataset} demonstrate {improvement}% improvement over baselines.",
            "We achieve state-of-the-art results on {benchmark} with {metric}.",
            "Our approach shows {adjective} improvements in {metric} across {number} tasks.",
            "Extensive evaluation reveals {benefit} compared to existing methods.",
        ]

        # Generate components
        tasks = [
            "image classification",
            "object detection",
            "language understanding",
            "machine translation",
        ]
        methods = [
            "transformer architectures",
            "graph neural networks",
            "contrastive learning",
            "meta-learning",
        ]
        concepts = [
            "self-supervision",
            "multi-modal learning",
            "few-shot learning",
            "transfer learning",
        ]
        techniques = [
            "attention mechanisms",
            "data augmentation",
            "knowledge distillation",
            "adversarial training",
        ]
        benefits = [
            "improved efficiency",
            "better generalization",
            "reduced computational cost",
            "enhanced robustness",
        ]
        adjectives = ["efficient", "scalable", "robust", "novel", "effective"]
        actions = ["optimizes", "learns", "adapts to", "processes"]
        targets = [
            "large-scale data",
            "complex patterns",
            "diverse domains",
            "real-world scenarios",
        ]
        challenges = [
            "data scarcity",
            "computational constraints",
            "domain shift",
            "class imbalance",
        ]
        datasets = ["ImageNet", "COCO", "GLUE", "WMT", "CIFAR-100"]
        benchmarks = [
            "standard benchmarks",
            "challenging datasets",
            "real-world applications",
        ]
        metrics = ["accuracy", "F1 score", "BLEU score", "mAP", "perplexity"]

        intro = self.random.choice(intro_templates).format(
            task=self.random.choice(tasks),
            method=self.random.choice(methods),
            concept=self.random.choice(concepts),
        )

        method = self.random.choice(method_templates).format(
            technique1=self.random.choice(techniques),
            technique2=self.random.choice(techniques),
            benefit=self.random.choice(benefits),
            adjective=self.random.choice(adjectives),
            action=self.random.choice(actions),
            target=self.random.choice(targets),
            challenge=self.random.choice(challenges),
        )

        result = self.random.choice(result_templates).format(
            dataset=self.random.choice(datasets),
            improvement=self.random.randint(5, 25),
            benchmark=self.random.choice(benchmarks),
            metric=self.random.choice(metrics),
            adjective=self.random.choice(adjectives),
            number=self.random.randint(3, 10),
            benefit=self.random.choice(benefits),
        )

        return f"{intro} {method} {result}"

    def _generate_keywords(self) -> List[str]:
        """Generate list of keywords."""
        num_keywords = self.random.randint(3, 7)
        return list(self.random.sample(self.KEYWORDS, num_keywords))

    def _generate_computational_analysis(self) -> ComputationalAnalysis:
        """Generate computational analysis data."""
        # Computational richness score
        computational_richness = self.random.uniform(0.1, 1.0)

        # Keyword matches for computational resources
        keyword_matches = {
            "gpu": self.random.randint(0, 10),
            "tpu": self.random.randint(0, 3),
            "training": self.random.randint(0, 15),
            "model": self.random.randint(0, 20),
            "parameters": self.random.randint(0, 5),
            "dataset": self.random.randint(0, 8),
            "memory": self.random.randint(0, 5),
            "compute": self.random.randint(0, 7),
        }

        # Resource metrics
        gpu_hours = None
        gpu_type = None
        if self.random.random() < 0.6:  # 60% mention GPU resources
            if self.random.random() < 0.3:  # Small experiments
                gpu_hours = self.random.uniform(0.1, 10.0)
            elif self.random.random() < 0.8:  # Medium experiments
                gpu_hours = self.random.uniform(10.0, 1000.0)
            else:  # Large experiments
                gpu_hours = self.random.uniform(1000.0, 50000.0)

            gpu_type = self.random.choice(self.GPU_TYPES)

        resource_metrics = {
            "gpu_hours": gpu_hours,
            "gpu_type": gpu_type,
            "model_parameters": self.random.randint(1000000, 175000000000)
            if self.random.random() < 0.5
            else None,
            "training_time_hours": gpu_hours * self.random.uniform(0.8, 1.2)
            if gpu_hours
            else None,
            "dataset_size": self.random.randint(1000, 1000000000)
            if self.random.random() < 0.4
            else None,
        }

        # Experimental indicators
        experimental_indicators = {
            "has_ablation_study": self.random.random() < 0.6,
            "has_hyperparameter_tuning": self.random.random() < 0.7,
            "has_multiple_runs": self.random.random() < 0.5,
            "reports_variance": self.random.random() < 0.3,
            "uses_validation_set": self.random.random() < 0.9,
            "uses_test_set": self.random.random() < 0.95,
        }

        # Confidence score based on how much information is available
        info_count = sum(
            [
                gpu_hours is not None,
                resource_metrics["model_parameters"] is not None,
                resource_metrics["dataset_size"] is not None,
                sum(keyword_matches.values()) > 20,
                computational_richness > 0.7,
            ]
        )
        confidence_score = min(0.3 + (info_count * 0.15), 1.0)

        return ComputationalAnalysis(
            computational_richness=computational_richness,
            keyword_matches=keyword_matches,
            resource_metrics=resource_metrics,
            experimental_indicators=experimental_indicators,
            confidence_score=confidence_score,
        )

    def _generate_authorship_analysis(
        self, authors: List[Author]
    ) -> AuthorshipAnalysis:
        """Generate authorship analysis based on authors."""
        academic_count = 0
        industry_count = 0
        unknown_count = 0
        author_details = []

        for author in authors:
            detail = {
                "name": author.name,
                "affiliation": author.affiliation or "Unknown",
                "category": "unknown",
            }

            if author.affiliation:
                # Check if academic or industry
                affiliation_lower = author.affiliation.lower()
                if any(
                    keyword in affiliation_lower
                    for keyword in [
                        "university",
                        "college",
                        "institute",
                        "school",
                        "academia",
                        "eth",
                        "epfl",
                        "mit",
                        "stanford",
                        "oxford",
                        "cambridge",
                    ]
                ):
                    academic_count += 1
                    detail["category"] = "academic"
                elif any(
                    keyword in affiliation_lower
                    for keyword in [
                        "research",
                        "labs",
                        "inc",
                        "corp",
                        "company",
                        "ltd",
                        "google",
                        "microsoft",
                        "meta",
                        "apple",
                        "nvidia",
                        "openai",
                    ]
                ):
                    industry_count += 1
                    detail["category"] = "industry"
                else:
                    unknown_count += 1
            else:
                unknown_count += 1

            author_details.append(detail)

        # Determine category based on counts
        total_authors = len(authors)
        if total_authors == 0:
            category = "needs_manual_review"
            confidence = 0.0
        elif academic_count == total_authors:
            category = "academic_eligible"
            confidence = 0.95
        elif industry_count > 0 and academic_count == 0:
            category = "industry_eligible"
            confidence = 0.9
        elif unknown_count > total_authors * 0.5:
            category = "needs_manual_review"
            confidence = 0.3
        elif academic_count > industry_count * 2:
            category = "academic_eligible"
            confidence = 0.8
        else:
            category = "industry_eligible"
            confidence = 0.7

        return AuthorshipAnalysis(
            category=category,
            academic_count=academic_count,
            industry_count=industry_count,
            unknown_count=unknown_count,
            confidence=confidence,
            author_details=author_details,
        )

    def _generate_venue_analysis(self, venue: str) -> VenueAnalysis:
        """Generate venue analysis based on venue name."""
        # Top-tier venues get higher scores
        top_tier_venues = [
            "NeurIPS",
            "ICML",
            "ICLR",
            "CVPR",
            "ICCV",
            "ACL",
            "AAAI",
            "IJCAI",
        ]
        second_tier_venues = [
            "ECCV",
            "EMNLP",
            "KDD",
            "SIGIR",
            "WWW",
            "COLT",
            "UAI",
            "AISTATS",
        ]
        workshop_venues = ["Workshop on ML", "Symposium on AI", "Conference on DL"]

        venue_upper = venue.upper()

        if any(v.upper() in venue_upper for v in top_tier_venues):
            venue_score = self.random.uniform(0.85, 1.0)
            importance_ranking = self.random.randint(1, 10)
        elif any(v.upper() in venue_upper for v in second_tier_venues):
            venue_score = self.random.uniform(0.7, 0.85)
            importance_ranking = self.random.randint(10, 30)
        elif any(v.upper() in venue_upper for v in workshop_venues):
            venue_score = self.random.uniform(0.4, 0.6)
            importance_ranking = self.random.randint(50, 100)
        elif "arxiv" in venue.lower():
            venue_score = self.random.uniform(0.3, 0.5)
            importance_ranking = self.random.randint(100, 200)
        else:
            venue_score = self.random.uniform(0.5, 0.7)
            importance_ranking = self.random.randint(30, 60)

        # Domain relevance and computational focus correlate with venue type
        if any(
            keyword in venue_upper for keyword in ["ML", "AI", "NEURAL", "LEARNING"]
        ):
            domain_relevance = self.random.uniform(0.8, 1.0)
            computational_focus = self.random.uniform(0.7, 0.95)
        elif any(
            keyword in venue_upper for keyword in ["COMPUTER", "VISION", "ROBOTICS"]
        ):
            domain_relevance = self.random.uniform(0.7, 0.9)
            computational_focus = self.random.uniform(0.6, 0.85)
        else:
            domain_relevance = self.random.uniform(0.4, 0.7)
            computational_focus = self.random.uniform(0.3, 0.6)

        return VenueAnalysis(
            venue_score=venue_score,
            domain_relevance=domain_relevance,
            computational_focus=computational_focus,
            importance_ranking=importance_ranking,
        )
