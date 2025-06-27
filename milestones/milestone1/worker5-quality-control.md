# Worker 5: Quality Control Framework

## Agent ID: worker5
## Work Stream: Quality Control and Validation Systems
## Duration: 1-2 hours
## Dependencies: Worker 0 (Architecture Setup) - MUST complete first

## Objective
Build comprehensive quality control framework for validating paper collection, ensuring data integrity, and generating validation reports.

## Deliverables
1. **Sanity Check System**: Automated validation of expected institutions and patterns
2. **Citation Verification**: Cross-source citation validation and outlier detection
3. **Quality Metrics**: Comprehensive quality assessment framework
4. **Report Generation**: Automated reporting and issue flagging system

## Detailed Tasks

### Task 5.1: Sanity Check Framework (30 minutes)
```python
# File: src/quality/validators/sanity_checker.py
class SanityChecker:
    def __init__(self):
        self.expected_academic_institutions = [
            'MIT', 'Stanford', 'CMU', 'Berkeley', 'Oxford', 'Cambridge',
            'ETH Zurich', 'University of Toronto', 'NYU', 'Princeton',
            'Harvard', 'Yale', 'University of Washington', 'EPFL',
            'McGill', 'Mila', 'Vector Institute'
        ]
        
        self.expected_industry_organizations = [
            'Google', 'Google Research', 'DeepMind', 'OpenAI',
            'Microsoft Research', 'Meta AI', 'Apple', 'Amazon',
            'NVIDIA', 'Anthropic', 'Cohere', 'IBM Research'
        ]
        
        self.expected_venues_by_domain = {
            'Computer Vision': ['CVPR', 'ICCV', 'ECCV', 'MICCAI'],
            'NLP': ['ACL', 'EMNLP', 'NAACL', 'CoNLL'],
            'RL': ['AAMAS', 'ICRA', 'IROS'],
            'ML General': ['NeurIPS', 'ICML', 'ICLR']
        }
    
    def check_institutional_coverage(self, papers, paper_type='academic'):
        """Verify expected institution representation in collected papers"""
        
        expected_orgs = (self.expected_academic_institutions if paper_type == 'academic' 
                        else self.expected_industry_organizations)
        
        found_institutions = set()
        institution_paper_counts = {}
        
        for paper in papers:
            for author in paper.get('authors', []):
                affiliation = author.get('affiliation', '').lower()
                
                for expected_org in expected_orgs:
                    if expected_org.lower() in affiliation:
                        found_institutions.add(expected_org)
                        institution_paper_counts[expected_org] = (
                            institution_paper_counts.get(expected_org, 0) + 1
                        )
        
        missing_institutions = set(expected_orgs) - found_institutions
        coverage_percentage = len(found_institutions) / len(expected_orgs)
        
        return {
            'coverage_percentage': coverage_percentage,
            'found_institutions': list(found_institutions),
            'missing_institutions': list(missing_institutions),
            'institution_paper_counts': institution_paper_counts,
            'quality_flag': 'low_coverage' if coverage_percentage < 0.3 else 'acceptable'
        }
    
    def check_domain_balance(self, papers):
        """Verify reasonable distribution across research domains"""
        
        domain_counts = {}
        for paper in papers:
            domain = paper.get('mila_domain', 'Unknown')
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        total_papers = len(papers)
        domain_percentages = {
            domain: count / total_papers 
            for domain, count in domain_counts.items()
        }
        
        # Flag domains with suspicious distributions
        quality_flags = []
        for domain, percentage in domain_percentages.items():
            if percentage > 0.5:  # No domain should dominate >50%
                quality_flags.append(f'domain_imbalance_{domain}')
            elif percentage < 0.05 and total_papers > 100:  # Domains shouldn't be <5%
                quality_flags.append(f'domain_underrepresented_{domain}')
        
        return {
            'domain_distribution': domain_percentages,
            'domain_counts': domain_counts,
            'total_papers': total_papers,
            'quality_flags': quality_flags
        }
    
    def check_temporal_balance(self, papers):
        """Verify reasonable distribution across years 2019-2024"""
        
        year_counts = {}
        for paper in papers:
            year = paper.get('year', paper.get('collection_year', 'Unknown'))
            year_counts[year] = year_counts.get(year, 0) + 1
        
        expected_years = list(range(2019, 2025))
        missing_years = [year for year in expected_years if year not in year_counts]
        
        # Check for reasonable year distribution
        total_papers = len(papers)
        year_percentages = {year: count / total_papers for year, count in year_counts.items()}
        
        quality_flags = []
        for year in expected_years:
            percentage = year_percentages.get(year, 0)
            if percentage < 0.05:  # Each year should have >5% representation
                quality_flags.append(f'year_underrepresented_{year}')
        
        return {
            'year_distribution': year_percentages,
            'year_counts': year_counts,
            'missing_years': missing_years,
            'quality_flags': quality_flags
        }
```

**Progress Documentation**: Create `status/worker5-sanity-checks.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "sanity_check_categories": 3,
  "validation_rules": 12,
  "test_coverage": {
    "institutional_coverage": true,
    "domain_balance": true,
    "temporal_balance": true
  },
  "issues": []
}
```

### Task 5.2: Citation Verification System (30 minutes)
```python
# File: src/quality/validators/citation_validator.py
class CitationValidator:
    def __init__(self):
        self.citation_thresholds = {
            2024: {'min': 5, 'max': 10000},
            2023: {'min': 10, 'max': 15000},
            2022: {'min': 20, 'max': 20000},
            2021: {'min': 30, 'max': 25000},
            2020: {'min': 50, 'max': 30000},
            2019: {'min': 75, 'max': 35000}
        }
    
    def validate_citation_counts(self, papers):
        """Cross-validate citation counts and detect outliers"""
        
        validation_results = {
            'total_papers': len(papers),
            'citation_issues': [],
            'outliers': [],
            'source_consistency': {},
            'suspicious_patterns': []
        }
        
        for paper in papers:
            paper_year = paper.get('year', 2024)
            citations = paper.get('citations', 0)
            sources = paper.get('all_sources', [paper.get('source', 'unknown')])
            
            # Check citation count reasonableness
            thresholds = self.citation_thresholds.get(paper_year, {'min': 5, 'max': 10000})
            
            if citations < thresholds['min']:
                validation_results['citation_issues'].append({
                    'paper_title': paper.get('title', 'Unknown'),
                    'year': paper_year,
                    'citations': citations,
                    'issue': 'below_minimum_threshold',
                    'expected_min': thresholds['min']
                })
            
            if citations > thresholds['max']:
                validation_results['outliers'].append({
                    'paper_title': paper.get('title', 'Unknown'),
                    'year': paper_year,
                    'citations': citations,
                    'issue': 'unusually_high_citations',
                    'sources': sources
                })
            
            # Track source consistency
            for source in sources:
                if source not in validation_results['source_consistency']:
                    validation_results['source_consistency'][source] = {
                        'paper_count': 0,
                        'avg_citations': 0,
                        'citation_sum': 0
                    }
                
                source_stats = validation_results['source_consistency'][source]
                source_stats['paper_count'] += 1
                source_stats['citation_sum'] += citations
                source_stats['avg_citations'] = source_stats['citation_sum'] / source_stats['paper_count']
        
        return validation_results
    
    def detect_suspicious_patterns(self, papers):
        """Identify papers with suspicious citation patterns"""
        
        suspicious = []
        
        # Check for identical citation counts (suspicious)
        citation_counts = {}
        for paper in papers:
            citations = paper.get('citations', 0)
            if citations not in citation_counts:
                citation_counts[citations] = []
            citation_counts[citations].append(paper.get('title', 'Unknown'))
        
        # Flag citation counts that appear too frequently
        for citations, titles in citation_counts.items():
            if len(titles) > 5 and citations > 100:  # More than 5 papers with same high citation count
                suspicious.append({
                    'issue': 'identical_citation_counts',
                    'citation_count': citations,
                    'paper_count': len(titles),
                    'papers': titles[:3]  # First 3 examples
                })
        
        return suspicious
```

**Progress Documentation**: Update `status/worker5-citation-validation.json`

### Task 5.3: Quality Metrics Framework (45 minutes)
```python
# File: src/quality/metrics.py
class QualityAssessment:
    def __init__(self):
        self.quality_weights = {
            'institutional_coverage': 0.25,
            'citation_reliability': 0.20,
            'computational_content': 0.20,
            'domain_balance': 0.15,
            'temporal_balance': 0.10,
            'venue_coverage': 0.10
        }
    
    def assess_collection_quality(self, papers, classification_results=None):
        """Comprehensive quality assessment of paper collection"""
        
        assessment = {
            'overall_score': 0,
            'component_scores': {},
            'quality_flags': [],
            'recommendations': [],
            'metadata': {
                'total_papers': len(papers),
                'assessment_timestamp': datetime.now().isoformat()
            }
        }
        
        # Institutional coverage assessment
        academic_coverage = self.sanity_checker.check_institutional_coverage(
            [p for p in papers if p.get('benchmark_type') == 'academic'], 'academic'
        )
        industry_coverage = self.sanity_checker.check_institutional_coverage(
            [p for p in papers if p.get('benchmark_type') == 'industry'], 'industry'
        )
        
        institutional_score = (academic_coverage['coverage_percentage'] + 
                             industry_coverage['coverage_percentage']) / 2
        assessment['component_scores']['institutional_coverage'] = institutional_score
        
        # Citation reliability assessment
        citation_validation = self.citation_validator.validate_citation_counts(papers)
        citation_reliability = 1.0 - (len(citation_validation['citation_issues']) / len(papers))
        assessment['component_scores']['citation_reliability'] = citation_reliability
        
        # Computational content assessment
        if any('computational_analysis' in paper for paper in papers):
            high_comp = len([p for p in papers 
                           if p.get('computational_analysis', {}).get('computational_richness', 0) > 0.6])
            computational_score = high_comp / len(papers)
        else:
            computational_score = 0.5  # Default if not analyzed
        assessment['component_scores']['computational_content'] = computational_score
        
        # Domain balance assessment
        domain_balance = self.sanity_checker.check_domain_balance(papers)
        domain_score = 1.0 - (len(domain_balance['quality_flags']) / 10)  # Penalty for flags
        assessment['component_scores']['domain_balance'] = max(domain_score, 0)
        
        # Temporal balance assessment
        temporal_balance = self.sanity_checker.check_temporal_balance(papers)
        temporal_score = 1.0 - (len(temporal_balance['quality_flags']) / 6)  # 6 years
        assessment['component_scores']['temporal_balance'] = max(temporal_score, 0)
        
        # Venue coverage assessment
        unique_venues = len(set(paper.get('venue', 'Unknown') for paper in papers))
        venue_score = min(unique_venues / 30, 1.0)  # Expect 30+ unique venues
        assessment['component_scores']['venue_coverage'] = venue_score
        
        # Calculate overall score
        overall_score = sum(
            score * self.quality_weights.get(component, 0)
            for component, score in assessment['component_scores'].items()
        )
        assessment['overall_score'] = overall_score
        
        # Generate recommendations
        assessment['recommendations'] = self.generate_quality_recommendations(assessment)
        
        return assessment
    
    def generate_quality_recommendations(self, assessment):
        """Generate actionable recommendations based on quality assessment"""
        
        recommendations = []
        scores = assessment['component_scores']
        
        if scores.get('institutional_coverage', 0) < 0.5:
            recommendations.append({
                'priority': 'high',
                'category': 'institutional_coverage',
                'recommendation': 'Add papers from missing top-tier institutions',
                'action': 'manual_curation'
            })
        
        if scores.get('citation_reliability', 0) < 0.8:
            recommendations.append({
                'priority': 'medium',
                'category': 'citation_reliability',
                'recommendation': 'Re-validate citation counts for flagged papers',
                'action': 'citation_reverification'
            })
        
        if scores.get('computational_content', 0) < 0.6:
            recommendations.append({
                'priority': 'high',
                'category': 'computational_content',
                'recommendation': 'Prioritize papers with higher computational richness',
                'action': 'content_filtering'
            })
        
        return recommendations
```

**Progress Documentation**: Create `status/worker5-quality-metrics.json`

### Task 5.4: Report Generation System (15 minutes)
```python
# File: src/quality/reporter.py
class QualityReporter:
    def generate_milestone1_report(self, papers, quality_assessment, collection_stats):
        """Generate comprehensive Milestone 1 completion report"""
        
        report = {
            'milestone': 'Milestone 1: Paper Collection',
            'completion_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_papers_collected': len(papers),
                'academic_papers': len([p for p in papers if p.get('benchmark_type') == 'academic']),
                'industry_papers': len([p for p in papers if p.get('benchmark_type') == 'industry']),
                'overall_quality_score': quality_assessment['overall_score'],
                'collection_success': quality_assessment['overall_score'] > 0.7
            },
            'detailed_metrics': quality_assessment,
            'collection_statistics': collection_stats,
            'next_steps': self.generate_next_steps(quality_assessment),
            'files_generated': [
                'academic_benchmark_papers.json',
                'industry_benchmark_papers.json',
                'quality_assessment_report.json',
                'collection_metadata.json'
            ]
        }
        
        return report
    
    def generate_next_steps(self, quality_assessment):
        """Generate recommended next steps based on quality assessment"""
        
        next_steps = []
        
        if quality_assessment['overall_score'] > 0.8:
            next_steps.append("Proceed to Milestone 2: Extraction Pipeline Development")
        elif quality_assessment['overall_score'] > 0.6:
            next_steps.extend([
                "Address quality recommendations before proceeding",
                "Consider targeted manual curation for critical gaps"
            ])
        else:
            next_steps.extend([
                "Significant quality issues identified - recommend collection review",
                "Focus on institutional coverage and computational content improvements"
            ])
        
        return next_steps
```

**Progress Documentation**: Create `status/worker5-reporting.json`

## Output Files
- `package/sanity_checks.py` - Comprehensive sanity check framework
- `package/citation_validator.py` - Citation verification and validation
- `package/quality_metrics.py` - Quality assessment framework
- `package/quality_reporter.py` - Report generation system
- `status/worker5-*.json` - Progress documentation files

## Success Criteria
- [ ] Sanity check framework covers institutions, domains, and temporal balance
- [ ] Citation validation detects outliers and suspicious patterns
- [ ] Quality metrics provide actionable assessment scores
- [ ] Report generation system ready for final milestone summary
- [ ] Progress documentation complete for orchestration

## Coordination Points
- **No dependencies**: Can start immediately
- **Outputs needed by**: Worker 7 (Final Selection) and Orchestration Agent
- **Status updates**: Every 30 minutes to `status/worker5-overall.json`
- **Integration point**: Quality assessment runs on final collected papers

## Risk Mitigation
- **Quality threshold tuning**: Conservative thresholds with manual override capability
- **Validation accuracy**: Extensive testing on known paper collections
- **Report completeness**: Comprehensive coverage of all quality dimensions
- **Flag sensitivity**: Balance between catching issues and false positives

## Communication Protocol
Update `status/worker5-overall.json` every 30 minutes:
```json
{
  "worker_id": "worker5",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 85,
  "current_task": "Task 5.3: Quality Metrics Framework",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "ready_for_handoff": true,
  "framework_components": {
    "sanity_checks": "completed",
    "citation_validation": "completed",
    "quality_metrics": "in_progress",
    "reporting": "pending"
  },
  "outputs_available": ["sanity_checks.py", "citation_validator.py"]
}
```