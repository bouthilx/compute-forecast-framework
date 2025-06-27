# Author Affiliation Filtering Strategy

## Academic Benchmark Affiliation Rules

### Majority Academic Requirement
- **>75% academic authors**: University, research institute, or academic lab affiliations
- **<25% industry authors**: Company affiliations (Google, Meta, Microsoft, etc.)
- **Collaborative research acceptable**: Industry-academic partnerships encouraged

### Implementation Strategy

```python
def classify_author_affiliation(affiliation):
    """Classify author affiliation as academic or industry"""
    
    academic_keywords = [
        'university', 'institut', 'college', 'school',
        'research center', 'laboratory', 'academia',
        'department of', 'faculty of'
    ]
    
    industry_keywords = [
        'google', 'microsoft', 'meta', 'facebook', 'openai',
        'deepmind', 'amazon', 'apple', 'nvidia', 'intel',
        'corporation', 'inc.', 'ltd.', 'llc'
    ]
    
    affiliation_lower = affiliation.lower()
    
    if any(keyword in affiliation_lower for keyword in academic_keywords):
        return 'academic'
    elif any(keyword in affiliation_lower for keyword in industry_keywords):
        return 'industry'
    else:
        return 'unknown'  # Manual review needed

def filter_majority_academic(papers):
    """Filter papers to those with >75% academic authors"""
    
    filtered_papers = []
    
    for paper in papers:
        academic_count = 0
        industry_count = 0
        
        for author in paper.authors:
            affiliation_type = classify_author_affiliation(author.affiliation)
            
            if affiliation_type == 'academic':
                academic_count += 1
            elif affiliation_type == 'industry':
                industry_count += 1
            # 'unknown' affiliations don't count toward either category
        
        total_classified = academic_count + industry_count
        
        if total_classified > 0:
            industry_percentage = industry_count / total_classified
            
            if industry_percentage < 0.25:  # <25% industry authors
                filtered_papers.append(paper)
                
    return filtered_papers
```

### Boundary Cases and Special Handling

#### Academic-Industry Joint Labs
- **Google Research** (when in academic collaboration): Count as industry
- **Microsoft Research Cambridge**: Count as industry 
- **Meta AI Research** (FAIR): Count as industry
- **Industry researchers with academic affiliations**: Use primary affiliation

#### Research Institutes
- **Max Planck Institute**: Academic
- **Allen Institute for AI**: Academic (non-profit research)
- **Mila, Vector Institute**: Academic
- **OpenAI** (research papers): Industry

#### Government Labs
- **National labs** (NIST, NASA, etc.): Count as academic
- **Military research**: Count as academic
- **Government agencies**: Count as academic

### Quality Control

#### Manual Review Triggers
- **Unknown affiliations >20%**: Manual classification needed
- **Borderline industry percentage** (20-30%): Manual review
- **Prestigious papers with unclear affiliations**: Priority for manual classification

#### Validation Checks
- **Sanity test**: Ensure major academic institutions represented
- **Industry distribution**: Check that collaborative papers aren't systematically excluded
- **Temporal consistency**: Verify filtering doesn't create bias over time

### Expected Impact on Collection

#### Inclusion Examples
- **Academic-led collaborations**: University researchers with Google/Meta co-authors
- **Visiting researcher papers**: Industry researchers at academic institutions
- **Joint grants**: Academic-industry research partnerships
- **Student internships**: Papers from students at industry labs during internships

#### Exclusion Examples
- **Pure industry papers**: All authors from company research labs
- **Industry-dominated**: Papers with >25% industry authors
- **Company technical reports**: Non-peer-reviewed industry publications

### Affiliation Data Sources

#### Primary Sources
- **Paper metadata**: Author affiliation strings from venues
- **Google Scholar**: Author institution information
- **Semantic Scholar**: Enhanced author affiliation data
- **DBLP**: Computer science author affiliation database

#### Backup Strategies
- **Manual lookup**: For unclear or missing affiliations
- **LinkedIn/academic pages**: Author current institution verification
- **Historical data**: Institution at time of publication vs. current

### Implementation Timeline

#### Automated Classification (2 hours)
- Develop affiliation classification rules
- Apply to collected papers automatically
- Flag uncertain cases for manual review

#### Manual Review (1 hour)
- Review flagged papers with unclear affiliations
- Validate borderline cases (20-30% industry)
- Quality check classification accuracy

#### Validation (30 minutes)
- Verify expected institutions represented
- Check for systematic exclusion patterns
- Confirm temporal consistency

### Success Metrics
- **Academic representation**: Expected institutions (MIT, Stanford, etc.) present
- **Collaboration inclusion**: Industry-academic partnerships represented
- **Classification accuracy**: >90% correct affiliation classification
- **Collection size**: Minimal reduction from strict academic-only filtering