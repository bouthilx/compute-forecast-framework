# Milestone 1: Organization Sanity Check Lists

## Academic Organization Sanity Check List

### Top-Tier US Universities
```python
us_universities = [
    # Ivy League + Stanford/MIT
    'MIT', 'Massachusetts Institute of Technology',
    'Stanford University', 'Stanford',
    'Harvard University', 'Harvard', 
    'Princeton University', 'Princeton',
    'Yale University', 'Yale',
    'Columbia University', 'Columbia',
    'University of Pennsylvania', 'UPenn',
    'Cornell University', 'Cornell',
    
    # Top Public Universities
    'UC Berkeley', 'University of California Berkeley', 'Berkeley',
    'UCLA', 'University of California Los Angeles',
    'University of Washington', 'UW',
    'University of Michigan', 'Michigan',
    'Georgia Tech', 'Georgia Institute of Technology',
    'UT Austin', 'University of Texas Austin',
    
    # Top Private Universities
    'Carnegie Mellon University', 'CMU',
    'NYU', 'New York University',
    'University of Chicago', 'UChicago',
    'Northwestern University',
    'Caltech', 'California Institute of Technology',
    'Johns Hopkins University'
]

international_universities = [
    # UK Universities
    'University of Oxford', 'Oxford University', 'Oxford',
    'University of Cambridge', 'Cambridge University', 'Cambridge',
    'Imperial College London', 'Imperial College',
    'University College London', 'UCL',
    'University of Edinburgh', 'Edinburgh',
    
    # Canadian Universities
    'University of Toronto', 'UofT',
    'McGill University', 'McGill',
    'University of British Columbia', 'UBC',
    'University of Montreal', 'Montreal',
    
    # European Universities
    'ETH Zurich', 'Swiss Federal Institute',
    'EPFL', 'École Polytechnique Fédérale',
    'Technical University of Munich', 'TUM',
    'Max Planck Institute', 'MPI',
    'University of Amsterdam', 'Amsterdam',
    'KTH Royal Institute', 'KTH',
    
    # Asian Universities
    'University of Tokyo', 'Tokyo',
    'Tsinghua University', 'Tsinghua',
    'Peking University', 'PKU',
    'National University of Singapore', 'NUS',
    'KAIST', 'Korea Advanced Institute'
]

research_institutes = [
    # AI-focused Research Institutes
    'Mila', 'Quebec AI Institute',
    'Vector Institute', 'Vector',
    'Allen Institute for AI', 'AI2',
    'Toyota Research Institute', 'TRI',
    'Honda Research Institute',
    
    # Government/Non-profit Research
    'NASA', 'National Aeronautics',
    'NIST', 'National Institute of Standards',
    'Lawrence Berkeley National Laboratory',
    'Argonne National Laboratory',
    'Los Alamos National Laboratory',
    
    # International Research Institutes
    'INRIA', 'French National Institute',
    'CNRS', 'Centre National de la Recherche',
    'Fraunhofer Institute',
    'RIKEN', 'Institute of Physical and Chemical'
]

expected_academic_orgs = us_universities + international_universities + research_institutes
```

## Industry Organization Sanity Check List

### Big Tech AI Labs
```python
big_tech_ai = [
    # Google/Alphabet
    'Google', 'Google Research', 'Google AI', 'Google Brain',
    'DeepMind', 'Google DeepMind', 'Alphabet',
    
    # Microsoft
    'Microsoft', 'Microsoft Research', 'MSR',
    'Microsoft AI', 'Azure AI',
    
    # Meta/Facebook
    'Meta', 'Meta AI', 'Facebook', 'Facebook AI',
    'FAIR', 'Facebook AI Research',
    
    # OpenAI
    'OpenAI', 'Open AI',
    
    # Apple
    'Apple', 'Apple Inc', 'Apple Machine Learning',
    
    # Amazon
    'Amazon', 'Amazon Web Services', 'AWS',
    'Amazon AI', 'Alexa AI',
    
    # Other Big Tech
    'NVIDIA', 'NVIDIA Research', 'NVIDIA AI',
    'Intel', 'Intel Labs', 'Intel AI',
    'IBM', 'IBM Research', 'IBM Watson',
    'Adobe', 'Adobe Research',
    'Salesforce', 'Salesforce Research'
]

ai_focused_companies = [
    # AI Startups/Scale-ups
    'Anthropic',
    'Cohere', 'Cohere AI',
    'Hugging Face',
    'Stability AI',
    'Character.AI', 'Character AI',
    'Adept', 'Adept AI',
    'Inflection AI', 'Inflection',
    'Midjourney',
    'Runway', 'Runway AI',
    
    # Autonomous Vehicles
    'Tesla', 'Tesla AI',
    'Waymo',
    'Cruise', 'GM Cruise',
    'Aurora', 'Aurora AI',
    'Argo AI',
    
    # Robotics
    'Boston Dynamics',
    'Agility Robotics',
    'Figure AI', 'Figure',
    'Embodied Intelligence'
]

international_industry = [
    # Chinese Tech
    'Baidu', 'Baidu Research',
    'Tencent', 'Tencent AI',
    'Alibaba', 'Alibaba DAMO',
    'ByteDance', 'TikTok AI',
    'SenseTime',
    'Megvii', 'Face++',
    
    # European Tech
    'SAP', 'SAP Research',
    'Siemens', 'Siemens Research',
    'Bosch', 'Robert Bosch',
    'DeepL',
    'Mistral AI',
    
    # Other International
    'Samsung', 'Samsung Research',
    'Sony', 'Sony AI',
    'NEC', 'NEC Research',
    'NTT', 'NTT Research'
]

expected_industry_orgs = big_tech_ai + ai_focused_companies + international_industry
```

## Sanity Check Implementation

### Coverage Validation Function
```python
def validate_organization_coverage(papers, expected_orgs, org_type='academic'):
    """Validate that expected organizations are represented in collected papers"""
    
    found_orgs = set()
    org_paper_counts = defaultdict(int)
    
    for paper in papers:
        for author in paper.get('authors', []):
            affiliation = author.get('affiliation', '').lower()
            
            for org in expected_orgs:
                if org.lower() in affiliation:
                    found_orgs.add(org)
                    org_paper_counts[org] += 1
                    break  # Don't double-count same org for same paper
    
    missing_orgs = set(expected_orgs) - found_orgs
    coverage_percentage = len(found_orgs) / len(expected_orgs)
    
    validation_result = {
        'org_type': org_type,
        'total_expected': len(expected_orgs),
        'found_count': len(found_orgs),
        'missing_count': len(missing_orgs),
        'coverage_percentage': coverage_percentage,
        'found_orgs': sorted(list(found_orgs)),
        'missing_orgs': sorted(list(missing_orgs)),
        'org_paper_counts': dict(org_paper_counts),
        'status': 'PASS' if coverage_percentage >= 0.3 else 'FAIL'
    }
    
    return validation_result

def print_coverage_report(academic_validation, industry_validation):
    """Print formatted coverage report"""
    
    print("="*80)
    print("ORGANIZATION COVERAGE REPORT")
    print("="*80)
    
    # Academic Coverage
    print(f"\nACADEMIC ORGANIZATIONS:")
    print(f"Coverage: {academic_validation['found_count']}/{academic_validation['total_expected']} "
          f"({academic_validation['coverage_percentage']:.1%}) - {academic_validation['status']}")
    
    print(f"\nTop Academic Organizations Found:")
    for org, count in sorted(academic_validation['org_paper_counts'].items(), 
                           key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {org}: {count} papers")
    
    if academic_validation['missing_orgs']:
        print(f"\nNotable Missing Academic Organizations:")
        for org in academic_validation['missing_orgs'][:10]:
            print(f"  - {org}")
    
    # Industry Coverage
    print(f"\nINDUSTRY ORGANIZATIONS:")
    print(f"Coverage: {industry_validation['found_count']}/{industry_validation['total_expected']} "
          f"({industry_validation['coverage_percentage']:.1%}) - {industry_validation['status']}")
    
    print(f"\nTop Industry Organizations Found:")
    for org, count in sorted(industry_validation['org_paper_counts'].items(), 
                           key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {org}: {count} papers")
    
    if industry_validation['missing_orgs']:
        print(f"\nNotable Missing Industry Organizations:")
        for org in industry_validation['missing_orgs'][:10]:
            print(f"  - {org}")
    
    print("="*80)
```

### Issue Detection and Flagging
```python
def detect_collection_issues(academic_validation, industry_validation):
    """Detect potential issues with paper collection"""
    
    issues = []
    
    # Academic coverage issues
    if academic_validation['coverage_percentage'] < 0.2:
        issues.append({
            'type': 'CRITICAL',
            'category': 'academic_coverage',
            'message': f"Very low academic coverage ({academic_validation['coverage_percentage']:.1%})",
            'recommendation': 'Review search queries and venue selection for academic papers'
        })
    elif academic_validation['coverage_percentage'] < 0.3:
        issues.append({
            'type': 'WARNING',
            'category': 'academic_coverage',
            'message': f"Low academic coverage ({academic_validation['coverage_percentage']:.1%})",
            'recommendation': 'Consider manual addition of papers from missing institutions'
        })
    
    # Industry coverage issues
    if industry_validation['coverage_percentage'] < 0.15:
        issues.append({
            'type': 'CRITICAL',
            'category': 'industry_coverage',
            'message': f"Very low industry coverage ({industry_validation['coverage_percentage']:.1%})",
            'recommendation': 'Review industry paper collection strategy'
        })
    elif industry_validation['coverage_percentage'] < 0.25:
        issues.append({
            'type': 'WARNING',
            'category': 'industry_coverage',
            'message': f"Low industry coverage ({industry_validation['coverage_percentage']:.1%})",
            'recommendation': 'Consider targeted search for missing industry organizations'
        })
    
    # Missing critical organizations
    critical_academic_missing = [
        'MIT', 'Stanford', 'CMU', 'Berkeley', 'Oxford', 'Cambridge'
    ]
    
    missing_critical_academic = [org for org in critical_academic_missing 
                               if org in academic_validation['missing_orgs']]
    
    if missing_critical_academic:
        issues.append({
            'type': 'WARNING',
            'category': 'missing_critical_academic',
            'message': f"Missing critical academic institutions: {missing_critical_academic}",
            'recommendation': 'Manual search for papers from these top institutions'
        })
    
    critical_industry_missing = [
        'Google', 'OpenAI', 'DeepMind', 'Meta', 'Microsoft'
    ]
    
    missing_critical_industry = [org for org in critical_industry_missing 
                               if org in industry_validation['missing_orgs']]
    
    if missing_critical_industry:
        issues.append({
            'type': 'WARNING',
            'category': 'missing_critical_industry',
            'message': f"Missing critical industry organizations: {missing_critical_industry}",
            'recommendation': 'Manual search for breakthrough papers from these organizations'
        })
    
    return issues

def print_issues_report(issues):
    """Print formatted issues report"""
    
    if not issues:
        print("\n✅ No major collection issues detected!")
        return
    
    print("\n" + "="*80)
    print("COLLECTION ISSUES DETECTED")
    print("="*80)
    
    critical_issues = [i for i in issues if i['type'] == 'CRITICAL']
    warning_issues = [i for i in issues if i['type'] == 'WARNING']
    
    if critical_issues:
        print(f"\n🚨 CRITICAL ISSUES ({len(critical_issues)}):")
        for issue in critical_issues:
            print(f"  ❌ {issue['message']}")
            print(f"     → {issue['recommendation']}\n")
    
    if warning_issues:
        print(f"\n⚠️  WARNINGS ({len(warning_issues)}):")
        for issue in warning_issues:
            print(f"  ⚠️  {issue['message']}")
            print(f"     → {issue['recommendation']}\n")
    
    print("="*80)
```

## Expected Coverage Thresholds

### Academic Organizations
- **Minimum acceptable**: 30% coverage
- **Good coverage**: 50% coverage  
- **Excellent coverage**: 70% coverage

**Critical institutions that MUST be present:**
- MIT, Stanford, CMU, Berkeley (US top 4 for AI)
- Oxford, Cambridge (UK top 2)
- At least 2-3 other top US universities
- At least 1-2 top international universities

### Industry Organizations  
- **Minimum acceptable**: 20% coverage
- **Good coverage**: 40% coverage
- **Excellent coverage**: 60% coverage

**Critical organizations that MUST be present:**
- Google/DeepMind (dominant in AI research)
- OpenAI (transformer/LLM breakthroughs)
- Meta AI (computer vision, multimodal)
- Microsoft Research (broad AI research)
- At least 2-3 other major tech companies

## Manual Review Triggers

### Automatic Flags for Manual Review
1. **Coverage below thresholds**: Academic <30% or Industry <20%
2. **Missing critical institutions**: Any of the "must be present" organizations missing
3. **Domain imbalance**: Any domain with <50% expected coverage
4. **Temporal imbalance**: Any year with <50% expected papers
5. **Citation anomalies**: Papers with suspiciously high/low citations for their year

### Manual Addition Strategy
If sanity checks fail, implement targeted manual search:
1. **Direct institution search**: Search specifically for missing critical organizations
2. **Venue-specific search**: Check major venues (NeurIPS, ICML, ICLR) for missing institutions
3. **Citation tracking**: Use highly-cited papers to find missing organizations
4. **Collaboration network**: Follow co-authorship patterns to find missing institutions

This comprehensive sanity check system ensures the paper collection captures the expected breadth of academic and industry research while flagging potential issues for manual correction.