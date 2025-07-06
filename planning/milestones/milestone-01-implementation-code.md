# Milestone 1: Paper Collection Implementation Plan

## Implementation Architecture

### Overall Workflow
```python
def collect_benchmark_papers():
    """Main pipeline for collecting benchmark papers"""

    # Phase 1: Analyze Mila corpus (2-3 hours)
    mila_analysis = analyze_mila_corpus()

    # Phase 2: Collect academic benchmarks (3-4 hours)
    academic_papers = collect_academic_benchmarks(mila_analysis)

    # Phase 3: Collect industry benchmarks (2-3 hours)
    industry_papers = collect_industry_benchmarks(mila_analysis)

    # Phase 4: Quality control (1-2 hours)
    validated_papers = validate_collection(academic_papers, industry_papers, mila_analysis)

    return validated_papers
```

## Phase 1: Mila Corpus Analysis Implementation

### Setup and Data Loading
```python
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import re

def load_mila_corpus():
    """Load and organize Mila paper corpus (2019-2024)"""

    # Expected data structure
    mila_papers = pd.read_csv('mila_papers_2019_2024.csv')
    # Columns: title, authors, venue, year, abstract, doi, etc.

    return mila_papers

def extract_venues(mila_papers):
    """Extract conference/journal venues where Mila publishes"""

    venue_counts = Counter(mila_papers['venue'])

    # Filter for venues with minimum publication count
    min_papers = 3  # At least 3 Mila papers over 6 years
    significant_venues = {venue: count for venue, count in venue_counts.items()
                         if count >= min_papers}

    # Categorize venues by type
    venues_by_type = {
        'ml_conferences': [],
        'domain_conferences': [],
        'journals': []
    }

    # ML conferences
    ml_conferences = ['NeurIPS', 'ICML', 'ICLR', 'AAAI', 'IJCAI']
    for venue in significant_venues:
        if any(conf in venue for conf in ml_conferences):
            venues_by_type['ml_conferences'].append(venue)

    # Domain-specific conferences (will be identified from papers)
    # TODO: Implement domain-specific venue classification

    return significant_venues, venues_by_type
```

### Domain Extraction
```python
def extract_research_domains(mila_papers):
    """Extract research domains from Mila publications using clustering"""

    # Combine title and abstract for domain analysis
    text_data = mila_papers['title'] + ' ' + mila_papers['abstract'].fillna('')

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words='english',
        ngram_range=(1, 2)
    )

    tfidf_matrix = vectorizer.fit_transform(text_data)

    # K-means clustering to identify research domains
    n_domains = 8  # Start with 8 domains, adjust based on results
    kmeans = KMeans(n_clusters=n_domains, random_state=42)
    domain_labels = kmeans.fit_predict(tfidf_matrix)

    # Add domain labels to dataframe
    mila_papers['domain_cluster'] = domain_labels

    # Extract top keywords for each domain
    feature_names = vectorizer.get_feature_names_out()
    domain_keywords = {}

    for i in range(n_domains):
        # Get top keywords for this cluster
        cluster_center = kmeans.cluster_centers_[i]
        top_indices = cluster_center.argsort()[-10:][::-1]
        top_keywords = [feature_names[idx] for idx in top_indices]
        domain_keywords[i] = top_keywords

    # Manual domain naming based on keywords
    domain_names = name_domains_from_keywords(domain_keywords)

    return domain_labels, domain_names, domain_keywords

def name_domains_from_keywords(domain_keywords):
    """Manually assign domain names based on top keywords"""

    domain_names = {}

    for domain_id, keywords in domain_keywords.items():
        keywords_str = ' '.join(keywords)

        # Pattern matching for domain identification
        if any(word in keywords_str for word in ['language', 'nlp', 'text', 'transformer']):
            domain_names[domain_id] = 'NLP/Language Models'
        elif any(word in keywords_str for word in ['vision', 'image', 'visual', 'cnn']):
            domain_names[domain_id] = 'Computer Vision'
        elif any(word in keywords_str for word in ['reinforcement', 'rl', 'policy', 'agent']):
            domain_names[domain_id] = 'Reinforcement Learning'
        elif any(word in keywords_str for word in ['graph', 'node', 'network', 'gnn']):
            domain_names[domain_id] = 'Graph Neural Networks'
        # Add more patterns as needed
        else:
            domain_names[domain_id] = f'Domain_{domain_id}'  # Fallback

    return domain_names
```

## Phase 2: Universal Paper Collection Implementation

### Citation Data Collection (Same for Academic & Industry)
```python
from scholarly import scholarly
import requests
import time
from urllib.parse import quote

def setup_citation_apis():
    """Setup API connections for citation data"""

    # Semantic Scholar API (free, no key needed)
    SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"

    # Google Scholar via scholarly library
    # scholarly.use_proxy(http='proxy_url', https='proxy_url')  # If needed

    return SEMANTIC_SCHOLAR_BASE

def get_papers_from_venue_year(venue, year, min_citations=10):
    """Get top-cited papers from specific venue and year"""

    papers = []

    # Method 1: Google Scholar search
    try:
        search_query = f'venue:"{venue}" year:{year}'
        search_results = scholarly.search_pubs(search_query)

        for i, paper in enumerate(search_results):
            if i >= 50:  # Limit to top 50 results
                break

            if paper.get('num_citations', 0) >= min_citations:
                papers.append({
                    'title': paper.get('title'),
                    'authors': paper.get('author', []),
                    'venue': venue,
                    'year': year,
                    'citations': paper.get('num_citations', 0),
                    'source': 'google_scholar',
                    'url': paper.get('url', ''),
                    'paper_id': paper.get('scholar_id', '')
                })

        time.sleep(1)  # Rate limiting

    except Exception as e:
        print(f"Error searching Google Scholar for {venue} {year}: {e}")

    # Method 2: Semantic Scholar API (backup/validation)
    try:
        papers_semantic = get_semantic_scholar_papers(venue, year, min_citations)
        papers.extend(papers_semantic)
    except Exception as e:
        print(f"Error with Semantic Scholar for {venue} {year}: {e}")

    # Remove duplicates and sort by citations
    papers = deduplicate_papers(papers)
    papers = sorted(papers, key=lambda x: x['citations'], reverse=True)

    return papers[:10]  # Top 10 for this venue/year

def get_semantic_scholar_papers(venue, year, min_citations):
    """Backup method using Semantic Scholar API"""

    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    query = f'venue:{venue} year:{year}'
    params = {
        'query': query,
        'limit': 100,
        'fields': 'title,authors,venue,year,citationCount,url,paperId'
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        papers = []

        for paper in data.get('data', []):
            if paper.get('citationCount', 0) >= min_citations:
                papers.append({
                    'title': paper.get('title'),
                    'authors': paper.get('authors', []),
                    'venue': paper.get('venue'),
                    'year': paper.get('year'),
                    'citations': paper.get('citationCount', 0),
                    'source': 'semantic_scholar',
                    'url': paper.get('url', ''),
                    'paper_id': paper.get('paperId', '')
                })

        return papers

    return []
```

### Author Affiliation Filtering
```python
def classify_author_affiliation(affiliation):
    """Classify author affiliation as academic or industry"""

    if not affiliation:
        return 'unknown'

    affiliation_lower = affiliation.lower()

    # Academic keywords
    academic_keywords = [
        'university', 'institut', 'college', 'school',
        'research center', 'laboratory', 'academia',
        'department of', 'faculty of', 'cnrs', 'inria'
    ]

    # Industry keywords
    industry_keywords = [
        'google', 'microsoft', 'meta', 'facebook', 'openai',
        'deepmind', 'amazon', 'apple', 'nvidia', 'intel',
        'corporation', 'inc.', 'ltd.', 'llc', 'tesla'
    ]

    # Check academic first
    if any(keyword in affiliation_lower for keyword in academic_keywords):
        return 'academic'

    # Check industry
    if any(keyword in affiliation_lower for keyword in industry_keywords):
        return 'industry'

    return 'unknown'

def filter_majority_academic(papers):
    """Filter papers to those with >75% academic authors"""

    filtered_papers = []

    for paper in papers:
        academic_count = 0
        industry_count = 0
        unknown_count = 0

        for author in paper['authors']:
            # Handle different author format structures
            if isinstance(author, dict):
                affiliation = author.get('affiliation', '')
            else:
                affiliation = ''  # Will need manual review

            affiliation_type = classify_author_affiliation(affiliation)

            if affiliation_type == 'academic':
                academic_count += 1
            elif affiliation_type == 'industry':
                industry_count += 1
            else:
                unknown_count += 1

        total_classified = academic_count + industry_count

        if total_classified > 0:
            industry_percentage = industry_count / total_classified

            # Apply the <25% industry filter
            if industry_percentage < 0.25:
                paper['author_analysis'] = {
                    'academic_count': academic_count,
                    'industry_count': industry_count,
                    'unknown_count': unknown_count,
                    'industry_percentage': industry_percentage
                }
                filtered_papers.append(paper)
        else:
            # All authors have unknown affiliations - flag for manual review
            paper['needs_manual_review'] = True
            paper['review_reason'] = 'unknown_affiliations'
            filtered_papers.append(paper)

    return filtered_papers
```

## Phase 3: Industry Benchmark Collection Implementation

### Industry Source Tracking
```python
def collect_industry_benchmarks(mila_analysis):
    """Collect industry benchmark papers"""

    industry_sources = {
        'OpenAI': {
            'search_terms': ['openai', 'site:openai.com'],
            'author_filters': ['OpenAI', 'open ai']
        },
        'DeepMind': {
            'search_terms': ['deepmind', 'site:deepmind.com'],
            'author_filters': ['DeepMind', 'Google DeepMind']
        },
        'Meta AI': {
            'search_terms': ['meta ai', 'facebook ai', 'fair'],
            'author_filters': ['Meta', 'Facebook', 'FAIR']
        },
        'Google Research': {
            'search_terms': ['google research', 'google brain'],
            'author_filters': ['Google', 'Google Research', 'Google Brain']
        }
    }

    industry_papers = []

    for domain in mila_analysis['domains']:
        for year in range(2019, 2025):
            for company, source_info in industry_sources.items():
                papers = search_industry_papers(company, source_info, domain, year)
                industry_papers.extend(papers)

    return industry_papers

def search_industry_papers(company, source_info, domain, year):
    """Search for industry papers from specific company/domain/year"""

    papers = []

    # Construct search query
    domain_keywords = get_domain_keywords(domain)

    for search_term in source_info['search_terms']:
        query = f'{search_term} {domain_keywords} year:{year}'

        try:
            search_results = scholarly.search_pubs(query)

            for i, paper in enumerate(search_results):
                if i >= 20:  # Limit results
                    break

                # Verify industry authorship
                if has_industry_authors(paper, source_info['author_filters']):
                    papers.append({
                        'title': paper.get('title'),
                        'authors': paper.get('author', []),
                        'venue': paper.get('venue', ''),
                        'year': year,
                        'citations': paper.get('num_citations', 0),
                        'company': company,
                        'domain': domain,
                        'source': 'industry_search'
                    })

            time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"Error searching {company} papers: {e}")

    return papers
```

## Phase 4: Quality Control Implementation

### Validation and Organization
```python
def validate_collection(academic_papers, industry_papers, mila_analysis):
    """Comprehensive quality control and validation"""

    validation_results = {
        'academic_papers': academic_papers,
        'industry_papers': industry_papers,
        'quality_report': {}
    }

    # 1. Citation verification
    validation_results = verify_citations(validation_results)

    # 2. Computational content check
    validation_results = check_computational_content(validation_results)

    # 3. Sanity check for expected institutions
    validation_results = sanity_check_institutions(validation_results)

    # 4. Temporal and domain balance
    validation_results = check_balance(validation_results, mila_analysis)

    return validation_results

def verify_citations(validation_results):
    """Cross-verify citation counts across sources"""

    for paper_type in ['academic_papers', 'industry_papers']:
        for paper in validation_results[paper_type]:
            # Cross-check citations between Google Scholar and Semantic Scholar
            if paper.get('source') == 'google_scholar':
                semantic_citations = get_semantic_scholar_citations(paper)
                if semantic_citations:
                    paper['citations_semantic'] = semantic_citations

                    # Flag large discrepancies
                    if abs(paper['citations'] - semantic_citations) > 50:
                        paper['citation_discrepancy'] = True

    return validation_results

def check_computational_content(validation_results):
    """Quick check for computational content in papers"""

    computational_keywords = [
        'gpu', 'training', 'computational', 'resources', 'hardware',
        'compute', 'hours', 'flops', 'memory', 'cluster'
    ]

    for paper_type in ['academic_papers', 'industry_papers']:
        for paper in validation_results[paper_type]:
            # Check title and available abstract
            text = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()

            computational_score = sum(1 for keyword in computational_keywords if keyword in text)
            paper['computational_score'] = computational_score

            if computational_score == 0:
                paper['needs_content_review'] = True

    return validation_results
```

## Implementation Timeline

### Day Plan (8-10 hours total)
```python
def execute_milestone_1():
    """Execute the complete paper collection pipeline"""

    print("Starting Milestone 1: Paper Collection")

    # Phase 1: Mila Analysis (2-3 hours)
    print("Phase 1: Analyzing Mila corpus...")
    mila_papers = load_mila_corpus()
    venues, venue_types = extract_venues(mila_papers)
    domains, domain_names, domain_keywords = extract_research_domains(mila_papers)

    mila_analysis = {
        'papers': mila_papers,
        'venues': venues,
        'domains': domain_names,
        'domain_keywords': domain_keywords
    }

    # Phase 2: Academic Collection (3-4 hours)
    print("Phase 2: Collecting academic benchmarks...")
    academic_papers = collect_academic_benchmarks(mila_analysis)

    # Phase 3: Industry Collection (2-3 hours)
    print("Phase 3: Collecting industry benchmarks...")
    industry_papers = collect_industry_benchmarks(mila_analysis)

    # Phase 4: Quality Control (1-2 hours)
    print("Phase 4: Quality control and validation...")
    final_results = validate_collection(academic_papers, industry_papers, mila_analysis)

    # Save results
    save_results(final_results)

    print("Milestone 1 completed successfully!")
    return final_results
```

## Expected Deliverables

### Data Files
- `mila_analysis.json`: Domains, venues, research patterns
- `academic_benchmarks.json`: 180-360 academic papers with metadata
- `industry_benchmarks.json`: 180-360 industry papers with metadata
- `quality_report.json`: Validation results and flags

### Success Metrics
- **Coverage**: 5-10 papers per domain per year
- **Citation verification**: >95% papers with verified citations
- **Quality flags**: <10% papers needing manual review
- **Institution representation**: Expected academic institutions present

Ready to implement this collection strategy?
