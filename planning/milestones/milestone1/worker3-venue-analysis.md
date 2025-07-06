# Worker 3: Venue Analysis & Domain Mapping

## Agent ID: worker3
## Work Stream: Venue Analysis and Classification
## Duration: 2 hours
## Dependencies: Worker 0 (Architecture Setup), Read-only access to current domain analysis results

## Objective
Map academic venues to research domains and build venue importance scoring to enable targeted paper collection.

## Deliverables
1. **Venue-Domain Mapping**: Link conferences/journals to specific research domains
2. **Venue Importance Scoring**: Rank venues by relevance and computational focus
3. **Collection Strategy**: Optimized venue selection for each domain
4. **Venue Database**: Comprehensive venue metadata for paper collection

## Detailed Tasks

### Task 3.1: Current Mila Venue Analysis (30 minutes)
```python
# File: src/analysis/venues/venue_analyzer.py
def analyze_mila_venues():
    """Extract and categorize venues from current Mila publication data"""

    # Read current domain analysis results (READ-ONLY)
    domain_analysis = load_current_domain_results()

    # Extract venue patterns by domain
    venue_by_domain = {}
    for domain_id, domain_info in domain_analysis['domains'].items():
        domain_name = domain_analysis['domain_names'][domain_id]
        venues = domain_info['top_venues']

        venue_by_domain[domain_name] = {
            'primary_venues': list(venues.keys())[:3],
            'all_venues': venues,
            'paper_count': domain_info['paper_count']
        }

    return venue_by_domain
```

**Progress Documentation**: Create `status/worker3-mila-venues.json`
```json
{
  "timestamp": "2024-XX-XX HH:MM:SS",
  "status": "in_progress|completed|failed",
  "domain_results_loaded": true,
  "venues_by_domain": {
    "Computer Vision & Medical Imaging": {
      "venue_count": 15,
      "top_venues": ["CVPR", "ICCV", "ECCV", "MICCAI"]
    },
    "Natural Language Processing": {
      "venue_count": 12,
      "top_venues": ["ACL", "EMNLP", "NAACL", "ICLR"]
    }
  },
  "issues": []
}
```

### Task 3.2: Comprehensive Venue Database Building (45 minutes)
```python
# File: src/analysis/venues/venue_database.py
VENUE_DATABASE = {
    'computer_vision': {
        'tier1': ['CVPR', 'ICCV', 'ECCV'],
        'tier2': ['BMVC', 'WACV', 'ACCV'],
        'medical': ['MICCAI', 'IPMI', 'ISBI'],
        'specialized': ['3DV', 'ICCV Workshops']
    },
    'nlp': {
        'tier1': ['ACL', 'EMNLP', 'NAACL'],
        'tier2': ['COLING', 'EACL', 'CoNLL'],
        'specialized': ['WMT', 'SemEval']
    },
    'ml_general': {
        'tier1': ['NeurIPS', 'ICML', 'ICLR'],
        'tier2': ['AISTATS', 'UAI', 'COLT']
    },
    'reinforcement_learning': {
        'specialized': ['AAMAS', 'AAAI', 'IJCAI'],
        'robotics': ['ICRA', 'IROS', 'RSS']
    },
    # ... continue for all domains
}

class VenueClassifier:
    def classify_venue_domain(self, venue_name):
        """Determine primary research domain for a venue"""

    def get_venue_computational_score(self, venue_name):
        """Score venue by computational research focus (0-1)"""

    def rank_venues_by_importance(self, domain):
        """Rank venues by paper collection priority"""
```

**Progress Documentation**: Update `status/worker3-venue-database.json`

### Task 3.3: Venue Importance Scoring System (30 minutes)
```python
# File: src/analysis/venues/venue_scoring.py
class VenueScorer:
    def __init__(self):
        self.scoring_factors = {
            'mila_paper_count': 0.3,      # How much Mila publishes there
            'computational_focus': 0.25,   # Emphasis on computational work
            'citation_impact': 0.2,        # Venue prestige/impact
            'yearly_consistency': 0.15,    # Consistent publication venue
            'domain_specificity': 0.1      # Domain relevance
        }

    def calculate_venue_score(self, venue, domain, mila_data):
        """Comprehensive venue scoring for paper collection priority"""

        scores = {}

        # Mila publication frequency
        mila_papers = mila_data.get(venue, {})
        scores['mila_paper_count'] = min(len(mila_papers) / 10, 1.0)

        # Computational focus (manual scoring + keyword analysis)
        scores['computational_focus'] = self.assess_computational_focus(venue)

        # Citation impact (h5-index, venue rankings)
        scores['citation_impact'] = self.get_venue_impact_score(venue)

        # Yearly consistency (appears across multiple years)
        scores['yearly_consistency'] = self.assess_consistency(mila_papers)

        # Domain specificity
        scores['domain_specificity'] = self.assess_domain_match(venue, domain)

        # Weighted final score
        final_score = sum(
            scores[factor] * weight
            for factor, weight in self.scoring_factors.items()
        )

        return {
            'final_score': final_score,
            'component_scores': scores,
            'recommendation': 'high' if final_score > 0.7 else 'medium' if final_score > 0.4 else 'low'
        }
```

**Progress Documentation**: Create `status/worker3-scoring.json`

### Task 3.4: Collection Strategy Optimization (15 minutes)
```python
# File: src/analysis/venues/collection_strategy.py
def generate_collection_strategy():
    """Create optimized venue selection for each domain"""

    strategy = {}

    for domain in RESEARCH_DOMAINS:
        venue_scores = rank_venues_for_domain(domain)

        # Select top venues ensuring diversity
        strategy[domain] = {
            'primary_venues': venue_scores[:3],      # Top 3 for focused collection
            'secondary_venues': venue_scores[3:6],   # Backup venues
            'general_ml_venues': ['NeurIPS', 'ICML', 'ICLR'],  # Always include
            'papers_per_venue': 8,                   # Target per venue/year
            'citation_threshold_by_year': {
                2024: 10, 2023: 20, 2022: 30,
                2021: 50, 2020: 75, 2019: 100
            }
        }

    return strategy
```

**Progress Documentation**: Create `status/worker3-strategy.json`

## Output Files
- `package/venue_analyzer.py` - Mila venue analysis functions
- `package/venue_database.py` - Comprehensive venue categorization
- `package/venue_scoring.py` - Venue importance scoring system
- `package/collection_strategy.py` - Optimized collection strategies
- `status/worker3-*.json` - Progress documentation files

## Success Criteria
- [ ] All current Mila venues mapped to research domains
- [ ] 100+ venues categorized with computational focus scores
- [ ] Venue importance scoring system validated
- [ ] Collection strategy covers all domains with 3+ venues each
- [ ] Progress documentation complete for orchestration

## Coordination Points
- **Dependencies**: Read-only access to current domain analysis results
- **Outputs needed by**: Worker 6 (Paper Collection) - critical for venue selection
- **Status updates**: Every 30 minutes to `status/worker3-overall.json`
- **Domain data source**: Uses existing `domain_analysis` and `mila_papers` data

## Risk Mitigation
- **Missing venues**: Comprehensive database with backup venues per domain
- **Venue name variations**: Alias mapping for conference name variants
- **Scoring accuracy**: Manual validation of top-ranked venues
- **Collection gaps**: Ensure every domain has 3+ viable venues

## Communication Protocol
Update `status/worker3-overall.json` every 30 minutes:
```json
{
  "worker_id": "worker3",
  "last_update": "timestamp",
  "overall_status": "in_progress|completed|blocked|failed",
  "completion_percentage": 75,
  "current_task": "Task 3.3: Venue Importance Scoring",
  "estimated_completion": "timestamp",
  "blocking_issues": [],
  "ready_for_handoff": true,
  "venue_mapping_stats": {
    "domains_covered": 7,
    "venues_per_domain_avg": 12,
    "high_priority_venues": 25
  },
  "outputs_available": ["venue_analyzer.py", "venue_database.py", "venue_scoring.py"]
}
```
