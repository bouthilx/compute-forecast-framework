# Worker 7: Final Paper Selection & Classification

## Agent ID: worker7
## Work Stream: Academic/Industry Classification and Final Selection
## Duration: 1.5-2 hours
## Dependencies: Workers 0, 2, 5, 6 (Architecture, Organization Classification, Quality Control, Paper Collection)

## Objective
Process collected papers through academic/industry classification and select final benchmark datasets with quality validation.

## Deliverables
1. **Academic Benchmark Dataset**: 180-360 papers with >75% academic authorship
2. **Industry Benchmark Dataset**: 180-360 papers with >75% industry authorship
3. **Classification Report**: Detailed authorship analysis and confidence scores
4. **Final Quality Assessment**: Comprehensive validation using quality control framework

## Detailed Tasks

### Task 7.1: Load Dependencies and Collected Papers (15 minutes)
```python
# File: src/selection/final_selector.py
class FinalSelector:
    def __init__(self):
        self.paper_classifier = None
        self.quality_assessor = None
        self.collected_papers = []

    def setup_selection_environment(self):
        """Initialize all required systems from other workers"""

        # Load organization classifier (Worker 2)
        try:
            from ...analysis.classification.paper_classifier import PaperClassifier
            from ...analysis.classification.validator import ClassificationValidator

            self.paper_classifier = PaperClassifier()
            self.classification_validator = ClassificationValidator()

        except ImportError as e:
            raise Exception(f"Worker 2 outputs not available: {e}")

        # Load quality control system (Worker 5)
        try:
            from ...quality.metrics import QualityAssessment
            from ...quality.validators.sanity_checker import SanityChecker
            from ...quality.reporter import QualityReporter

            self.quality_assessor = QualityAssessment()
            self.sanity_checker = SanityChecker()
            self.quality_reporter = QualityReporter()

        except ImportError as e:
            raise Exception(f"Worker 5 outputs not available: {e}")

        # Load collected papers (Worker 6)
        try:
            with open('data/raw_collected_papers.json', 'r') as f:
                self.collected_papers = json.load(f)

            with open('data/collection_statistics.json', 'r') as f:
                self.collection_stats = json.load(f)

        except FileNotFoundError as e:
            raise Exception(f"Worker 6 outputs not available: {e}")

        print(f"Loaded {len(self.collected_papers)} papers for final selection")
        return True
```

**Progress Documentation**: Create `status/worker7-setup.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "dependencies_loaded": {
    "worker2_classification": true,
    "worker5_quality_control": true,
    "worker6_collected_papers": true
  },
  "papers_loaded": 1042,
  "classification_targets": {
    "academic_target": 300,
    "industry_target": 300,
    "papers_per_domain_year": 5
  },
  "issues": []
}
```

### Task 7.2: Academic/Industry Classification (45 minutes)
```python
# File: src/selection/authorship_classifier.py
def classify_all_papers(self):
    """Classify all collected papers as academic or industry eligible"""

    classification_results = {
        'academic_eligible': [],
        'industry_eligible': [],
        'needs_manual_review': [],
        'classification_stats': {
            'total_papers': len(self.collected_papers),
            'successful_classifications': 0,
            'failed_classifications': 0,
            'manual_review_required': 0
        }
    }

    print("Classifying papers by authorship...")

    for i, paper in enumerate(self.collected_papers):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(self.collected_papers)} papers")

        try:
            # Perform detailed authorship classification
            classification = self.paper_classifier.classify_paper_authorship(paper)

            # Store classification details in paper
            paper['authorship_analysis'] = classification

            # Route to appropriate category
            if classification['category'] == 'academic_eligible':
                classification_results['academic_eligible'].append(paper)
                classification_results['classification_stats']['successful_classifications'] += 1

            elif classification['category'] == 'industry_eligible':
                classification_results['industry_eligible'].append(paper)
                classification_results['classification_stats']['successful_classifications'] += 1

            else:  # needs_manual_review
                classification_results['needs_manual_review'].append(paper)
                classification_results['classification_stats']['manual_review_required'] += 1

        except Exception as e:
            paper['authorship_analysis'] = {
                'category': 'classification_failed',
                'error': str(e),
                'confidence': 0.0
            }
            classification_results['classification_stats']['failed_classifications'] += 1

    # Generate classification summary
    self.generate_classification_summary(classification_results)

    return classification_results

def generate_classification_summary(self, classification_results):
    """Generate detailed classification statistics"""

    stats = classification_results['classification_stats']

    print(f"\n=== Classification Summary ===")
    print(f"Total papers: {stats['total_papers']}")
    print(f"Academic eligible: {len(classification_results['academic_eligible'])}")
    print(f"Industry eligible: {len(classification_results['industry_eligible'])}")
    print(f"Manual review needed: {len(classification_results['needs_manual_review'])}")
    print(f"Classification failed: {stats['failed_classifications']}")

    # Analyze confidence distribution
    academic_confidences = [
        p['authorship_analysis']['confidence']
        for p in classification_results['academic_eligible']
        if 'confidence' in p['authorship_analysis']
    ]

    industry_confidences = [
        p['authorship_analysis']['confidence']
        for p in classification_results['industry_eligible']
        if 'confidence' in p['authorship_analysis']
    ]

    if academic_confidences:
        print(f"Academic avg confidence: {sum(academic_confidences)/len(academic_confidences):.3f}")
    if industry_confidences:
        print(f"Industry avg confidence: {sum(industry_confidences)/len(industry_confidences):.3f}")
```

**Progress Documentation**: Update `status/worker7-classification.json`

### Task 7.3: Final Paper Selection and Balancing (30 minutes)
```python
# File: src/selection/selectors/paper_selector.py
def select_final_benchmarks(self, classification_results, target_per_domain_year=5):
    """Select balanced final papers for academic and industry benchmarks"""

    final_selection = {
        'academic_benchmarks': [],
        'industry_benchmarks': [],
        'selection_metadata': {
            'target_per_domain_year': target_per_domain_year,
            'selection_criteria': [
                'citation_count_ranking',
                'computational_richness_score',
                'venue_importance',
                'domain_year_balance'
            ]
        }
    }

    # Group papers by domain and year for balanced selection
    academic_grouped = self.group_papers_by_domain_year(
        classification_results['academic_eligible']
    )

    industry_grouped = self.group_papers_by_domain_year(
        classification_results['industry_eligible']
    )

    # Select academic benchmarks with balanced representation
    print("Selecting academic benchmark papers...")
    for (domain, year), papers in academic_grouped.items():
        selected = self.select_top_papers_for_domain_year(
            papers, target_per_domain_year, 'academic'
        )

        # Add selection metadata
        for i, paper in enumerate(selected):
            paper['benchmark_type'] = 'academic'
            paper['selection_rank'] = i + 1
            paper['selection_criteria_scores'] = self.calculate_selection_scores(paper)

        final_selection['academic_benchmarks'].extend(selected)
        print(f"  Selected {len(selected)} papers for {domain} {year} (academic)")

    # Select industry benchmarks with balanced representation
    print("Selecting industry benchmark papers...")
    for (domain, year), papers in industry_grouped.items():
        selected = self.select_top_papers_for_domain_year(
            papers, target_per_domain_year, 'industry'
        )

        # Add selection metadata
        for i, paper in enumerate(selected):
            paper['benchmark_type'] = 'industry'
            paper['selection_rank'] = i + 1
            paper['selection_criteria_scores'] = self.calculate_selection_scores(paper)

        final_selection['industry_benchmarks'].extend(selected)
        print(f"  Selected {len(selected)} papers for {domain} {year} (industry)")

    return final_selection

def select_top_papers_for_domain_year(self, papers, target_count, benchmark_type):
    """Select top papers using multiple criteria"""

    # Calculate composite score for each paper
    scored_papers = []
    for paper in papers:
        composite_score = self.calculate_composite_selection_score(paper)
        scored_papers.append((composite_score, paper))

    # Sort by composite score (descending)
    scored_papers.sort(key=lambda x: x[0], reverse=True)

    # Select top papers up to target count
    selected_papers = [paper for score, paper in scored_papers[:target_count]]

    return selected_papers

def calculate_composite_selection_score(self, paper):
    """Calculate composite score for paper selection priority"""

    # Citation score (40% weight)
    citations = paper.get('citations', 0)
    max_citations = 1000  # Normalization factor
    citation_score = min(citations / max_citations, 1.0)

    # Computational richness score (30% weight)
    comp_analysis = paper.get('computational_analysis', {})
    comp_richness = comp_analysis.get('computational_richness', 0.0)

    # Venue importance score (20% weight)
    venue_score = paper.get('venue_score', 0.5)

    # Authorship confidence score (10% weight)
    auth_analysis = paper.get('authorship_analysis', {})
    auth_confidence = auth_analysis.get('confidence', 0.5)

    # Weighted composite score
    composite_score = (
        0.40 * citation_score +
        0.30 * comp_richness +
        0.20 * venue_score +
        0.10 * auth_confidence
    )

    return composite_score

def group_papers_by_domain_year(self, papers):
    """Group papers by domain and year for balanced selection"""

    grouped = defaultdict(list)

    for paper in papers:
        domain = paper.get('mila_domain', 'Unknown')
        year = paper.get('collection_year', paper.get('year', 0))
        grouped[(domain, year)].append(paper)

    return grouped
```

**Progress Documentation**: Create `status/worker7-selection.json`

### Task 7.4: Final Quality Assessment and Reporting (30 minutes)
```python
# File: src/selection/final_validator.py
def perform_final_quality_assessment(self, final_selection):
    """Comprehensive quality assessment of final benchmark datasets"""

    print("Performing final quality assessment...")

    # Combine all selected papers for assessment
    all_selected_papers = (
        final_selection['academic_benchmarks'] +
        final_selection['industry_benchmarks']
    )

    # Run comprehensive quality assessment
    quality_assessment = self.quality_assessor.assess_collection_quality(
        all_selected_papers, final_selection
    )

    # Perform sanity checks
    sanity_results = self.perform_detailed_sanity_checks(final_selection)

    # Generate final validation report
    validation_report = self.generate_final_validation_report(
        final_selection, quality_assessment, sanity_results
    )

    return validation_report

def perform_detailed_sanity_checks(self, final_selection):
    """Detailed sanity checks on final selection"""

    sanity_results = {}

    # Check academic institution coverage
    academic_papers = final_selection['academic_benchmarks']
    academic_coverage = self.sanity_checker.check_institutional_coverage(
        academic_papers, 'academic'
    )
    sanity_results['academic_institution_coverage'] = academic_coverage

    # Check industry organization coverage
    industry_papers = final_selection['industry_benchmarks']
    industry_coverage = self.sanity_checker.check_institutional_coverage(
        industry_papers, 'industry'
    )
    sanity_results['industry_organization_coverage'] = industry_coverage

    # Check domain balance
    all_papers = academic_papers + industry_papers
    domain_balance = self.sanity_checker.check_domain_balance(all_papers)
    sanity_results['domain_balance'] = domain_balance

    # Check temporal balance
    temporal_balance = self.sanity_checker.check_temporal_balance(all_papers)
    sanity_results['temporal_balance'] = temporal_balance

    return sanity_results

def generate_final_validation_report(self, final_selection, quality_assessment, sanity_results):
    """Generate comprehensive final validation report"""

    report = {
        'milestone1_completion': {
            'status': 'completed',
            'completion_timestamp': datetime.now().isoformat(),
            'total_papers_selected': len(final_selection['academic_benchmarks']) + len(final_selection['industry_benchmarks']),
            'academic_papers': len(final_selection['academic_benchmarks']),
            'industry_papers': len(final_selection['industry_benchmarks'])
        },
        'quality_assessment': quality_assessment,
        'sanity_check_results': sanity_results,
        'selection_statistics': self.generate_selection_statistics(final_selection),
        'success_metrics': self.evaluate_success_metrics(final_selection, quality_assessment),
        'recommendations': self.generate_final_recommendations(quality_assessment, sanity_results)
    }

    return report

def evaluate_success_metrics(self, final_selection, quality_assessment):
    """Evaluate against Milestone 1 success criteria"""

    total_papers = len(final_selection['academic_benchmarks']) + len(final_selection['industry_benchmarks'])

    success_metrics = {
        'paper_count_target': {
            'target': '360-720 papers',
            'actual': total_papers,
            'met': 360 <= total_papers <= 720
        },
        'quality_score_target': {
            'target': '>0.7 overall quality',
            'actual': quality_assessment['overall_score'],
            'met': quality_assessment['overall_score'] > 0.7
        },
        'academic_industry_balance': {
            'target': 'Balanced representation',
            'academic_count': len(final_selection['academic_benchmarks']),
            'industry_count': len(final_selection['industry_benchmarks']),
            'met': abs(len(final_selection['academic_benchmarks']) - len(final_selection['industry_benchmarks'])) < 100
        }
    }

    overall_success = all(metric['met'] for metric in success_metrics.values())
    success_metrics['overall_milestone_success'] = overall_success

    return success_metrics
```

**Progress Documentation**: Create `status/worker7-final-assessment.json`

## Output Files
- `data/academic_benchmark_papers.json` - Final academic benchmark dataset
- `data/industry_benchmark_papers.json` - Final industry benchmark dataset
- `data/classification_results.json` - Detailed classification analysis
- `reports/milestone1_completion_report.json` - Comprehensive completion report
- `status/worker7-*.json` - Progress documentation files

## Success Criteria
- [ ] 360-720 total papers selected across both benchmarks
- [ ] Academic/industry balance within reasonable range (<100 paper difference)
- [ ] >90% of papers successfully classified with confidence scores
- [ ] Overall quality assessment score >0.7
- [ ] All major domains and years represented in final selection

## Coordination Points
- **Critical Dependencies**:
  - Worker 2: Organization classification system must be functional
  - Worker 5: Quality control framework required for validation
  - Worker 6: Collected papers dataset must be complete
- **Final handoff**: Complete milestone with orchestration agent
- **Status updates**: Every 20 minutes during selection and validation

## Risk Mitigation
- **Classification failures**: Backup classification methods and manual review flags
- **Selection bias**: Multiple scoring criteria with balanced weighting
- **Quality thresholds**: Conservative quality requirements with override capability
- **Balance issues**: Dynamic adjustment of selection targets by domain

## Communication Protocol
Update `status/worker7-overall.json` every 20 minutes:
```json
{
  "worker_id": "worker7",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 90,
  "current_task": "Final Quality Assessment",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "selection_progress": {
    "papers_classified": 1042,
    "academic_selected": 287,
    "industry_selected": 293,
    "quality_score": 0.78
  },
  "milestone_ready": true,
  "outputs_available": [
    "academic_benchmark_papers.json",
    "industry_benchmark_papers.json",
    "milestone1_completion_report.json"
  ]
}
```
