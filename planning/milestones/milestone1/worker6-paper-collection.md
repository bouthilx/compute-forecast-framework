# Worker 6: Paper Collection Execution

## Agent ID: worker6
## Work Stream: Universal Paper Collection
## Duration: 3-4 hours
## Dependencies: Workers 0, 1, 3, 4 (Architecture, Citation APIs, Venue Analysis, Computational Content)

## Objective
Execute comprehensive paper collection across all research domains using prepared infrastructure and analysis systems.

## Deliverables
1. **Raw Paper Collection**: 800-1200 papers from available sources and domains
2. **Enriched Paper Metadata**: Papers with computational analysis and venue scoring
3. **Collection Statistics**: Detailed metrics on collection success rates
4. **Source Distribution**: Papers organized by collection method and source
5. **Full-Scale Production Collection**: Complete dataset for Worker 7 classification

## Detailed Tasks

### Task 6.1: Pre-Collection Setup and Validation (30 minutes)
```python
# File: src/data/collectors/collection_executor.py
class CollectionExecutor:
    def __init__(self):
        self.citation_apis = None
        self.venue_analysis = None
        self.computational_analyzer = None
        self.rate_limiter = None

    def setup_collection_environment(self):
        """Initialize all required systems from other workers"""

        # Load citation infrastructure (Worker 1)
        try:
            from ...data.collectors.citation_collector import CitationCollector
            from ...data.sources.google_scholar import GoogleScholarSource
            from ...data.sources.semantic_scholar import SemanticScholarSource

            self.citation_apis = setup_citation_apis()
            self.rate_limiter = RateLimiter()
            self.paper_collector = PaperCollector()

            # Test API connectivity
            api_status = self.test_api_connectivity()
            working_apis = [api for api, status in api_status.items() if status]
            if len(working_apis) < 2:  # Require at least 2 working APIs
                raise Exception(f"Insufficient working APIs: {api_status}")
            else:
                print(f"Proceeding with {len(working_apis)} working APIs: {working_apis}")

        except ImportError as e:
            raise Exception(f"Worker 1 outputs not available: {e}")

        # Load venue analysis (Worker 3)
        try:
            from ...analysis.venues.venue_analyzer import analyze_mila_venues
            from ...analysis.venues.venue_database import VenueClassifier
            from ...analysis.venues.collection_strategy import generate_collection_strategy

            self.venue_analysis = analyze_mila_venues()
            self.venue_classifier = VenueClassifier()
            self.collection_strategy = generate_collection_strategy()

        except ImportError as e:
            raise Exception(f"Worker 3 outputs not available: {e}")

        # Load computational analyzer (Worker 4)
        try:
            from ...analysis.computational.analyzer import ComputationalAnalyzer
            from ...analysis.computational.filter import ComputationalFilter

            self.computational_analyzer = ComputationalAnalyzer()
            self.computational_filter = ComputationalFilter()

        except ImportError as e:
            raise Exception(f"Worker 4 outputs not available: {e}")

        # Load current domain analysis results
        self.domain_analysis = self.load_domain_results()

        return True

    def load_domain_results(self):
        """Load finalized domain analysis from ongoing work"""
        # This reads the latest domain analysis results
        # May need to coordinate with domain analysis agent
        try:
            with open('final_corrected_domain_stats.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback to existing analysis
            with open('domain_clusters.json', 'r') as f:
                return json.load(f)
```

**Progress Documentation**: Create `status/worker6-setup.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "dependencies_loaded": {
    "worker1_citation_apis": true,
    "worker3_venue_analysis": true,
    "worker4_computational_analyzer": true,
    "domain_analysis": true
  },
  "api_status": {
    "google_scholar": "ok",
    "semantic_scholar": "ok",
    "openalex": "ok"
  },
  "collection_targets": {
    "total_papers_target": 1000,
    "papers_per_domain_year": 8,
    "domains_count": 7,
    "years_span": 6
  },
  "issues": []
}
```

### Task 6.2: Domain-Based Collection Execution (2.5 hours)
```python
# File: src/data/collectors/domain_collector.py
def execute_domain_collection(self, target_per_domain_year=8):
    """Execute collection for each domain and year combination"""

    collection_results = {
        'raw_papers': [],
        'collection_stats': defaultdict(lambda: defaultdict(int)),
        'failed_searches': [],
        'source_distribution': defaultdict(int)
    }

    domains = self.get_domains_from_analysis()

    for domain_name in domains:
        print(f"\n=== Collecting papers for {domain_name} ===")

        for year in range(2019, 2025):
            print(f"Processing {domain_name} - {year}")

            year_papers = self.collect_domain_year_papers(
                domain_name, year, target_per_domain_year
            )

            # Enrich papers with computational analysis
            enriched_papers = self.enrich_papers_with_analysis(
                year_papers, domain_name, year
            )

            collection_results['raw_papers'].extend(enriched_papers)
            collection_results['collection_stats'][domain_name][year] = len(enriched_papers)

            # Track source distribution
            for paper in enriched_papers:
                source = paper.get('source', 'unknown')
                collection_results['source_distribution'][source] += 1

            print(f"  Collected {len(enriched_papers)} papers for {domain_name} {year}")

            # Rate limiting between domain/year combinations
            time.sleep(2)

    return collection_results

def collect_domain_year_papers(self, domain_name, year, target_count):
    """Collect papers for specific domain and year"""

    collected_papers = []

    # Method 1: Domain-specific venues
    domain_venues = self.collection_strategy[domain_name]['primary_venues']
    for venue in domain_venues[:3]:  # Top 3 venues per domain
        try:
            venue_papers = self.paper_collector.collect_from_venue_year(
                venue, year, self.get_citation_threshold(year)
            )
            collected_papers.extend(venue_papers)
            self.rate_limiter.wait('venue_search')

        except Exception as e:
            self.collection_results['failed_searches'].append({
                'venue': venue,
                'year': year,
                'domain': domain_name,
                'error': str(e)
            })

    # Method 2: Major ML venues with domain keywords
    major_venues = ['NeurIPS', 'ICML', 'ICLR']
    domain_keywords = self.get_domain_keywords(domain_name)

    for venue in major_venues:
        try:
            keyword_papers = self.paper_collector.collect_from_venue_year_with_keywords(
                venue, year, domain_keywords[:5], domain_name
            )
            collected_papers.extend(keyword_papers)
            self.rate_limiter.wait('keyword_search')

        except Exception as e:
            self.collection_results['failed_searches'].append({
                'venue': venue,
                'year': year,
                'domain': domain_name,
                'method': 'keyword_search',
                'error': str(e)
            })

    # Method 3: Direct keyword search (backup)
    if len(collected_papers) < target_count:
        try:
            keyword_papers = self.paper_collector.collect_from_keywords(
                domain_keywords, year, domain_name
            )
            collected_papers.extend(keyword_papers)

        except Exception as e:
            print(f"    Keyword search failed for {domain_name} {year}: {e}")

    # Remove duplicates and sort by citations
    unique_papers = self.deduplicate_papers(collected_papers)
    sorted_papers = sorted(unique_papers, key=lambda x: x.get('citations', 0), reverse=True)

    # Select top papers for this domain/year
    selected_papers = sorted_papers[:target_count]

    return selected_papers

def enrich_papers_with_analysis(self, papers, domain_name, year):
    """Add computational analysis and metadata to papers"""

    enriched_papers = []

    for paper in papers:
        # Add collection metadata
        paper['mila_domain'] = domain_name
        paper['collection_year'] = year
        paper['collection_timestamp'] = datetime.now().isoformat()

        # Add computational analysis
        try:
            computational_analysis = self.computational_analyzer.analyze_paper_content(paper)
            paper['computational_analysis'] = computational_analysis
        except Exception as e:
            paper['computational_analysis'] = {
                'error': str(e),
                'computational_richness': 0.0
            }

        # Add venue scoring
        try:
            venue = paper.get('venue', '')
            venue_score = self.venue_classifier.get_venue_computational_score(venue)
            paper['venue_score'] = venue_score
        except Exception as e:
            paper['venue_score'] = 0.5  # Default score

        enriched_papers.append(paper)

    return enriched_papers
```

**Progress Documentation**: Update `status/worker6-collection.json` every 30 minutes

### Task 6.3: Collection Validation and Statistics (30 minutes)
```python
# File: src/data/collectors/collection_validator.py
def validate_collection_results(self, collection_results):
    """Validate collection completeness and quality"""

    validation = {
        'collection_completeness': {},
        'quality_indicators': {},
        'coverage_gaps': [],
        'recommendations': []
    }

    # Check domain/year coverage
    expected_combinations = 7 * 6  # 7 domains × 6 years = 42 combinations
    actual_combinations = sum(
        1 for domain_stats in collection_results['collection_stats'].values()
        for year_count in domain_stats.values() if year_count > 0
    )

    validation['collection_completeness'] = {
        'expected_combinations': expected_combinations,
        'actual_combinations': actual_combinations,
        'coverage_percentage': actual_combinations / expected_combinations,
        'total_papers': len(collection_results['raw_papers'])
    }

    # Identify coverage gaps
    for domain, year_stats in collection_results['collection_stats'].items():
        for year in range(2019, 2025):
            if year_stats.get(year, 0) == 0:
                validation['coverage_gaps'].append({
                    'domain': domain,
                    'year': year,
                    'papers_found': 0
                })

    # Quality indicators
    papers_with_citations = len([
        p for p in collection_results['raw_papers']
        if p.get('citations', 0) > 0
    ])

    papers_with_computational_analysis = len([
        p for p in collection_results['raw_papers']
        if 'computational_analysis' in p
    ])

    validation['quality_indicators'] = {
        'papers_with_citations_pct': papers_with_citations / len(collection_results['raw_papers']),
        'papers_with_computational_analysis_pct': papers_with_computational_analysis / len(collection_results['raw_papers']),
        'avg_citations_per_paper': sum(p.get('citations', 0) for p in collection_results['raw_papers']) / len(collection_results['raw_papers']),
        'source_diversity': len(collection_results['source_distribution'])
    }

    # Generate recommendations
    if validation['collection_completeness']['coverage_percentage'] < 0.8:
        validation['recommendations'].append('Significant coverage gaps - consider additional collection methods')

    if validation['quality_indicators']['papers_with_citations_pct'] < 0.9:
        validation['recommendations'].append('High number of papers without citation data - verify API sources')

    return validation

def generate_collection_statistics(self, collection_results, validation):
    """Generate comprehensive collection statistics"""

    stats = {
        'collection_summary': {
            'total_papers_collected': len(collection_results['raw_papers']),
            'unique_domains': len(collection_results['collection_stats']),
            'years_covered': len(set(p.get('collection_year', p.get('year')) for p in collection_results['raw_papers'])),
            'collection_duration': 'calculated_from_timestamps',
            'success_rate': validation['collection_completeness']['coverage_percentage']
        },
        'source_breakdown': dict(collection_results['source_distribution']),
        'domain_distribution': {
            domain: sum(year_stats.values())
            for domain, year_stats in collection_results['collection_stats'].items()
        },
        'failed_searches': len(collection_results['failed_searches']),
        'quality_metrics': validation['quality_indicators']
    }

    return stats
```

**Progress Documentation**: Create `status/worker6-validation.json`

## Output Files
- `data/raw_collected_papers.json` - All collected papers with metadata
- `data/collection_statistics.json` - Detailed collection metrics
- `data/failed_searches.json` - Failed search attempts for debugging
- `status/worker6-*.json` - Progress documentation files
- **PROOF OF CONCEPT**: `data/simple_collected_papers.json` - 8 papers collected from working APIs
- **PROOF OF CONCEPT**: `data/simple_collection_stats.json` - Collection metrics from test run

## Success Criteria
- [x] Collection infrastructure implemented and tested
- [x] Multi-API integration working (Semantic Scholar + OpenAlex)
- [x] Domain-specific collection strategies developed
- [x] Paper enrichment pipeline operational
- [x] Collection validation framework created
- [x] **ISSUE IDENTIFIED**: Setup requires ALL APIs functional, but Google Scholar IP-blocked
- [x] **WORKAROUND PROVEN**: Collection works with available APIs (8 papers collected)
- [x] **FIXED**: Modified setup to accept partial API availability (2/3 APIs sufficient)
- [ ] **CRITICAL**: Execute full-scale collection with working APIs (Target: 800+ papers)
- [ ] **CRITICAL**: Achieve >80% coverage of domain/year combinations
- [ ] **CRITICAL**: Complete collection statistics and validation for Worker 7 handoff
- [ ] **REQUIRED**: Generate production dataset for academic/industry classification

## Coordination Points
- **Critical Dependencies**:
  - Worker 1: Citation APIs must be functional
  - Worker 3: Venue analysis and collection strategy required
  - Worker 4: Computational analyzer for paper enrichment
- **Domain analysis**: Requires current/final domain classification results
- **Outputs needed by**: Worker 7 (Final Selection) - immediate handoff
- **Status updates**: Every 30 minutes during collection execution

## Risk Mitigation
- **API failures**: Multiple backup sources per paper, accept partial API availability
- **Google Scholar IP blocking**: Focus collection on Semantic Scholar + OpenAlex
- **Rate limiting**: Conservative delays with exponential backoff
- **Collection gaps**: Multiple collection methods per domain/year
- **Data quality**: Validation and enrichment at collection time
- **Proven workaround**: Collection demonstrated working with 2/3 APIs (8 papers collected)

## Communication Protocol
Update `status/worker6-overall.json` every 30 minutes during collection:
```json
{
  "worker_id": "worker6",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 65,
  "current_task": "Collecting Computer Vision papers for 2022",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "collection_progress": {
    "domains_completed": 3,
    "domains_total": 7,
    "papers_collected": 456,
    "current_domain": "Computer Vision",
    "current_year": 2022
  },
  "ready_for_handoff": false,
  "outputs_available": ["raw_collected_papers.json (partial)"]
}
```

## Current Status & Next Steps

### Completed Work ✅
- Collection infrastructure fully implemented and tested
- API integration working for Semantic Scholar + OpenAlex
- Domain collector and collection executor created
- Paper enrichment pipeline operational
- Validation framework implemented
- **PROOF OF CONCEPT**: Successfully collected 8 papers from working APIs
- **INFRASTRUCTURE FIXES APPLIED**: Collection executor accepts partial API availability
- **WORKAROUND IMPLEMENTED**: System works with 2/3 APIs (Semantic Scholar + OpenAlex)

### Current Collection Status 📊
- **Infrastructure**: ✅ Complete and functional
- **Proof of Concept**: ✅ 8 papers successfully collected
- **Production Collection**: ❌ **INCOMPLETE** - Only 6.67% coverage
- **Worker 7 Readiness**: ❌ **INSUFFICIENT DATA** for classification

### Critical Gap Analysis 🚨
**Current State**: 8 papers from 1 domain (Computer Vision) × 2 years (2023-2024)
**Required State**: 800+ papers from 5 domains × 6 years (2019-2024)
**Coverage**: 6.67% vs 80%+ needed
**Impact**: Worker 7 cannot perform reliable academic/industry classification

### Immediate Action Required 🎯
1. **Execute full-scale collection** using working APIs (Semantic Scholar + OpenAlex)
2. **Target all 5 domains**: Computer Vision, NLP, RL, Graph Learning, Scientific Computing
3. **Cover all 6 years**: 2019-2024 for trend analysis
4. **Collect 800+ papers minimum** for statistical significance
5. **Generate comprehensive validation** for Worker 7 handoff

## Handoff to Worker 7

### Current Handoff Status: ❌ **NOT READY**
**Reason**: Insufficient data volume for reliable classification (8 papers vs 800+ needed)

### Requirements for Worker 7 Handoff:
1. **Minimum 800 papers collected** across all domains and years
2. **Coverage >80%** of domain/year combinations (24/30 combinations minimum)
3. **Complete collection validation** with quality metrics
4. **Source distribution** documented for reliability assessment
5. **Academic/industry classification feasibility** confirmed

### Completion Checklist:
- [ ] Execute full-scale collection with working APIs
- [ ] Achieve 800+ papers minimum target
- [ ] Cover all 5 research domains
- [ ] Span all 6 years (2019-2024)
- [ ] Generate final collection statistics
- [ ] Validate data quality for classification
- [ ] Update status to "completed" with ready_for_handoff: true
- [ ] Create handoff documentation for Worker 7

### Worker 7 Dependencies:
**BLOCKED**: Worker 7 cannot proceed with current 8-paper dataset
**UNBLOCKED WHEN**: 800+ papers collected and validated
**TIMELINE**: Full collection execution required before handoff
