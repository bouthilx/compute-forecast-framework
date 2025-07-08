# Worker 4: Computational Content Detection

## Agent ID: worker4
## Work Stream: Computational Resource Analysis
## Duration: 2-3 hours
## Dependencies: Worker 0 (Architecture Setup) - MUST complete first

## Objective
Build system to identify and score papers based on computational resource requirements and experimental content for resource projection accuracy.

## Deliverables
1. **Resource Keyword Extraction**: Identify GPU, compute, and training indicators
2. **Computational Richness Scoring**: Quantify computational content per paper
3. **Resource Pattern Recognition**: Detect training times, model sizes, dataset scales
4. **Filtering System**: Prioritize papers with actual resource requirements

## Detailed Tasks

### Task 4.1: Computational Keyword Database (45 minutes)
```python
# File: src/analysis/computational/keywords.py
COMPUTATIONAL_INDICATORS = {
    'gpu_hardware': [
        'GPU', 'V100', 'A100', 'H100', 'RTX', 'Tesla', 'CUDA',
        'graphics processing unit', 'parallel processing', 'NVIDIA',
        'TPU', 'tensor processing unit', 'cloud computing', 'distributed training'
    ],

    'training_resources': [
        'training time', 'compute hours', 'GPU hours', 'CPU hours',
        'wall-clock time', 'training duration', 'computational cost',
        'compute budget', 'resource consumption', 'energy consumption'
    ],

    'model_scale': [
        'parameters', 'billion parameters', 'million parameters',
        'model size', 'large model', 'transformer', 'neural network',
        'deep network', 'architecture', 'layers'
    ],

    'dataset_scale': [
        'dataset size', 'training data', 'million samples', 'billion tokens',
        'large dataset', 'data preprocessing', 'batch size',
        'mini-batch', 'data loading', 'storage requirements'
    ],

    'optimization_compute': [
        'hyperparameter tuning', 'grid search', 'random search',
        'neural architecture search', 'AutoML', 'optimization',
        'cross-validation', 'ablation study', 'experimental validation'
    ],

    'infrastructure': [
        'cluster', 'distributed', 'parallel', 'multi-gpu', 'multi-node',
        'high performance computing', 'HPC', 'supercomputer',
        'cloud platform', 'AWS', 'Google Cloud', 'Azure'
    ]
}

COMPUTATIONAL_PATTERNS = {
    # Regex patterns for extracting specific values
    'gpu_count': r'(\d+)\s*(?:x\s*)?(?:GPU|V100|A100|H100)',
    'training_time': r'(\d+(?:\.\d+)?)\s*(hours?|days?|weeks?)',
    'parameter_count': r'(\d+(?:\.\d+)?)\s*(?:million|billion|M|B)\s*parameters',
    'dataset_size': r'(\d+(?:\.\d+)?)\s*(?:million|billion|M|B|K)\s*(?:samples|examples|tokens)',
    'batch_size': r'batch\s*size\s*(?:of\s*)?(\d+)',
    'memory_usage': r'(\d+(?:\.\d+)?)\s*(?:GB|TB|MB)\s*(?:memory|RAM|VRAM)'
}
```

**Progress Documentation**: Create `status/worker4-keywords.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "keyword_categories": 6,
  "total_keywords": 75,
  "pattern_matchers": 6,
  "validation_tests": {
    "keyword_coverage": 0.85,
    "pattern_accuracy": 0.92
  },
  "issues": []
}
```

### Task 4.2: Content Analysis Engine (60 minutes)
```python
# File: src/analysis/computational/analyzer.py
class ComputationalAnalyzer:
    def __init__(self):
        self.keywords = COMPUTATIONAL_INDICATORS
        self.patterns = COMPUTATIONAL_PATTERNS

    def analyze_paper_content(self, paper):
        """Comprehensive computational content analysis"""

        # Extract text from title, abstract, and full text if available
        text_content = self.extract_paper_text(paper)

        # Keyword-based analysis
        keyword_scores = self.analyze_keywords(text_content)

        # Pattern-based extraction
        resource_metrics = self.extract_resource_metrics(text_content)

        # Computational richness scoring
        richness_score = self.calculate_richness_score(keyword_scores, resource_metrics)

        return {
            'computational_richness': richness_score,
            'keyword_matches': keyword_scores,
            'resource_metrics': resource_metrics,
            'experimental_indicators': self.detect_experimental_content(text_content),
            'recommendation': self.make_inclusion_recommendation(richness_score)
        }

    def analyze_keywords(self, text):
        """Count computational keyword occurrences by category"""
        text_lower = text.lower()
        scores = {}

        for category, keywords in self.keywords.items():
            matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
            scores[category] = {
                'matches': matches,
                'unique_keywords': len([k for k in keywords if k.lower() in text_lower]),
                'density': matches / len(text.split()) if text else 0
            }

        return scores

    def extract_resource_metrics(self, text):
        """Extract specific computational metrics using regex patterns"""
        metrics = {}

        for metric_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                metrics[metric_type] = {
                    'raw_matches': matches,
                    'normalized_values': self.normalize_metric_values(metric_type, matches)
                }

        return metrics

    def calculate_richness_score(self, keyword_scores, resource_metrics):
        """Calculate overall computational richness score (0-1)"""

        # Keyword contribution (40% of score)
        keyword_component = 0
        for category, scores in keyword_scores.items():
            # Weight different categories
            weight = {
                'gpu_hardware': 0.3,
                'training_resources': 0.25,
                'model_scale': 0.2,
                'dataset_scale': 0.15,
                'optimization_compute': 0.05,
                'infrastructure': 0.05
            }.get(category, 0.1)

            category_score = min(scores['matches'] / 5, 1.0)  # Cap at 5 matches
            keyword_component += weight * category_score

        # Resource metrics contribution (60% of score)
        metrics_component = 0
        if resource_metrics:
            metrics_weight = {
                'gpu_count': 0.2,
                'training_time': 0.2,
                'parameter_count': 0.2,
                'dataset_size': 0.15,
                'batch_size': 0.1,
                'memory_usage': 0.15
            }

            for metric, weight in metrics_weight.items():
                if metric in resource_metrics:
                    metrics_component += weight

        final_score = 0.4 * keyword_component + 0.6 * metrics_component
        return min(final_score, 1.0)
```

**Progress Documentation**: Update `status/worker4-analyzer.json`

### Task 4.3: Experimental Content Detection (30 minutes)
```python
# File: src/analysis/computational/experimental_detector.py
class ExperimentalDetector:
    def __init__(self):
        self.experimental_indicators = [
            'experiment', 'evaluation', 'benchmark', 'baseline',
            'results', 'performance', 'accuracy', 'precision', 'recall',
            'ablation', 'comparison', 'validation', 'test set',
            'training set', 'dataset', 'implementation', 'code'
        ]

        self.methodology_indicators = [
            'method', 'approach', 'algorithm', 'technique',
            'architecture', 'model', 'framework', 'system'
        ]

    def detect_experimental_content(self, text):
        """Identify papers with experimental/implementation content"""

        text_lower = text.lower()

        experimental_score = sum(
            1 for indicator in self.experimental_indicators
            if indicator in text_lower
        ) / len(self.experimental_indicators)

        methodology_score = sum(
            1 for indicator in self.methodology_indicators
            if indicator in text_lower
        ) / len(self.methodology_indicators)

        # Check for specific experimental sections
        has_results_section = any(
            phrase in text_lower
            for phrase in ['results section', 'experimental results', 'evaluation results']
        )

        has_implementation_details = any(
            phrase in text_lower
            for phrase in ['implementation details', 'hyperparameters', 'training details']
        )

        return {
            'experimental_score': experimental_score,
            'methodology_score': methodology_score,
            'has_results_section': has_results_section,
            'has_implementation_details': has_implementation_details,
            'is_experimental_paper': experimental_score > 0.3 or has_results_section
        }
```

**Progress Documentation**: Create `status/worker4-experimental.json`

### Task 4.4: Paper Filtering and Prioritization (45 minutes)
```python
# File: src/analysis/computational/filter.py
class ComputationalFilter:
    def __init__(self):
        self.thresholds = {
            'high_computational': 0.7,
            'medium_computational': 0.4,
            'low_computational': 0.2,
            'experimental_required': 0.3
        }

    def filter_papers_by_computational_content(self, papers):
        """Filter and prioritize papers based on computational content"""

        filtered_papers = {
            'high_priority': [],      # Rich computational content
            'medium_priority': [],    # Some computational content
            'low_priority': [],       # Minimal computational content
            'theoretical_only': []    # No computational indicators
        }

        for paper in papers:
            analysis = self.analyzer.analyze_paper_content(paper)

            richness = analysis['computational_richness']
            is_experimental = analysis['experimental_indicators']['is_experimental_paper']

            # Add analysis to paper metadata
            paper['computational_analysis'] = analysis

            # Prioritization logic
            if richness >= self.thresholds['high_computational'] and is_experimental:
                filtered_papers['high_priority'].append(paper)
            elif richness >= self.thresholds['medium_computational'] and is_experimental:
                filtered_papers['medium_priority'].append(paper)
            elif richness >= self.thresholds['low_computational'] or is_experimental:
                filtered_papers['low_priority'].append(paper)
            else:
                filtered_papers['theoretical_only'].append(paper)

        return filtered_papers

    def generate_computational_report(self, filtered_papers):
        """Generate summary of computational content analysis"""

        total_papers = sum(len(papers) for papers in filtered_papers.values())

        report = {
            'total_papers_analyzed': total_papers,
            'computational_distribution': {
                category: {
                    'count': len(papers),
                    'percentage': len(papers) / total_papers * 100
                }
                for category, papers in filtered_papers.items()
            },
            'resource_projection_quality': {
                'high_confidence': len(filtered_papers['high_priority']),
                'medium_confidence': len(filtered_papers['medium_priority']),
                'low_confidence': len(filtered_papers['low_priority']),
                'insufficient_data': len(filtered_papers['theoretical_only'])
            }
        }

        return report
```

**Progress Documentation**: Create `status/worker4-filtering.json`

## Output Files
- `package/computational_keywords.py` - Keyword database and patterns
- `package/computational_analyzer.py` - Content analysis engine
- `package/experimental_detector.py` - Experimental content detection
- `package/computational_filter.py` - Paper filtering and prioritization
- `status/worker4-*.json` - Progress documentation files

## Success Criteria
- [ ] 75+ computational keywords across 6 categories
- [ ] Pattern matching achieves >90% accuracy on test cases
- [ ] Computational richness scoring validated on sample papers
- [ ] Experimental content detection >85% accuracy
- [ ] Progress documentation complete for orchestration

## Coordination Points
- **No dependencies**: Can start immediately
- **Outputs needed by**: Worker 6 (Paper Collection) and Worker 7 (Final Selection)
- **Status updates**: Every 30 minutes to `status/worker4-overall.json`
- **Testing data**: Use current Mila papers for validation

## Risk Mitigation
- **Keyword completeness**: Comprehensive domain-specific keyword lists
- **Pattern accuracy**: Extensive regex testing and validation
- **Scoring calibration**: Manual validation on known computational papers
- **False positives**: Conservative thresholds with experimental validation

## Communication Protocol
Update `status/worker4-overall.json` every 30 minutes:
```json
{
  "worker_id": "worker4",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 80,
  "current_task": "Task 4.4: Paper Filtering",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "ready_for_handoff": true,
  "validation_metrics": {
    "keyword_coverage": 0.88,
    "pattern_accuracy": 0.92,
    "experimental_detection": 0.86
  },
  "outputs_available": ["computational_keywords.py", "computational_analyzer.py"]
}
```
