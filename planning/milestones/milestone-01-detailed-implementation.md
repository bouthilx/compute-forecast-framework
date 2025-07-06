# Milestone 1: Detailed Implementation Plan

## Universal Paper Collection Strategy

### Core Principle: Same Collection, Different Filtering
- **Collection method**: Identical for academic and industry papers
- **Data sources**: Same citation databases and search strategies
- **Filtering stage**: Apply academic vs industry criteria post-collection
- **Quality control**: Same validation process for both

## Detailed Implementation Steps

### Step 1: Mila Corpus Analysis (2.5 hours)

#### 1.1 Load and Organize Mila Data (30 minutes)
```python
def analyze_mila_corpus():
    """Complete analysis of Mila publication patterns"""
    
    # Load Mila papers (2019-2024)
    mila_papers = pd.read_csv('mila_papers_2019_2024.csv')
    
    # Expected columns: title, authors, venue, year, abstract, doi
    required_columns = ['title', 'authors', 'venue', 'year']
    validate_data_format(mila_papers, required_columns)
    
    return mila_papers

def validate_data_format(df, required_columns):
    """Ensure Mila data has required structure"""
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")
    
    print(f"Loaded {len(df)} Mila papers from {df['year'].min()}-{df['year'].max()}")
    print(f"Venues: {df['venue'].nunique()} unique venues")
    print(f"Years distribution: {df['year'].value_counts().sort_index()}")
```

#### 1.2 Extract Research Domains (90 minutes)
```python
def extract_research_domains_detailed(mila_papers):
    """Detailed domain extraction with validation"""
    
    # Combine text features for clustering
    text_features = []
    for _, paper in mila_papers.iterrows():
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        venue = paper.get('venue', '')
        text_features.append(f"{title} {abstract} {venue}")
    
    # TF-IDF Vectorization with domain-relevant parameters
    vectorizer = TfidfVectorizer(
        max_features=2000,
        stop_words='english',
        ngram_range=(1, 3),  # Include trigrams for technical terms
        min_df=2,  # Ignore very rare terms
        max_df=0.8  # Ignore very common terms
    )
    
    tfidf_matrix = vectorizer.fit_transform(text_features)
    
    # Try multiple cluster numbers to find optimal
    optimal_clusters = find_optimal_clusters(tfidf_matrix, range(6, 12))
    
    # Final clustering
    kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
    domain_labels = kmeans.fit_predict(tfidf_matrix)
    
    # Analyze clusters
    domain_analysis = analyze_domain_clusters(mila_papers, domain_labels, vectorizer, kmeans)
    
    return domain_analysis

def find_optimal_clusters(tfidf_matrix, cluster_range):
    """Find optimal number of clusters using silhouette score"""
    from sklearn.metrics import silhouette_score
    
    silhouette_scores = []
    for n_clusters in cluster_range:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(tfidf_matrix)
        score = silhouette_score(tfidf_matrix, labels)
        silhouette_scores.append(score)
    
    optimal_n = cluster_range[np.argmax(silhouette_scores)]
    print(f"Optimal clusters: {optimal_n} (silhouette score: {max(silhouette_scores):.3f})")
    
    return optimal_n

def analyze_domain_clusters(mila_papers, domain_labels, vectorizer, kmeans):
    """Analyze and name domain clusters"""
    
    feature_names = vectorizer.get_feature_names_out()
    n_clusters = len(set(domain_labels))
    
    domain_analysis = {
        'domains': {},
        'domain_names': {},
        'paper_distribution': {},
        'venue_distribution': {},
        'temporal_distribution': {}
    }
    
    for cluster_id in range(n_clusters):
        # Get papers in this cluster
        cluster_papers = mila_papers[domain_labels == cluster_id]
        
        # Extract top keywords
        cluster_center = kmeans.cluster_centers_[cluster_id]
        top_indices = cluster_center.argsort()[-15:][::-1]
        top_keywords = [feature_names[idx] for idx in top_indices]
        
        # Analyze venues for this domain
        venue_counts = cluster_papers['venue'].value_counts()
        
        # Analyze temporal distribution
        year_counts = cluster_papers['year'].value_counts()
        
        # Name domain based on keywords and venues
        domain_name = name_domain_from_analysis(top_keywords, venue_counts.index[:5])
        
        domain_analysis['domains'][cluster_id] = {
            'keywords': top_keywords,
            'paper_count': len(cluster_papers),
            'top_venues': venue_counts.head(5).to_dict(),
            'year_distribution': year_counts.to_dict()
        }
        
        domain_analysis['domain_names'][cluster_id] = domain_name
    
    return domain_analysis

def name_domain_from_analysis(keywords, top_venues):
    """Intelligent domain naming based on keywords and venues"""
    
    keywords_str = ' '.join(keywords).lower()
    venues_str = ' '.join(top_venues).lower()
    combined = f"{keywords_str} {venues_str}"
    
    # Domain classification rules
    if any(term in combined for term in ['language', 'nlp', 'text', 'transformer', 'bert', 'gpt']):
        return 'Natural Language Processing'
    elif any(term in combined for term in ['vision', 'image', 'visual', 'cnn', 'cvpr', 'iccv']):
        return 'Computer Vision'
    elif any(term in combined for term in ['reinforcement', 'rl', 'policy', 'agent', 'game']):
        return 'Reinforcement Learning'
    elif any(term in combined for term in ['graph', 'node', 'network', 'gnn']):
        return 'Graph Neural Networks'
    elif any(term in combined for term in ['audio', 'speech', 'sound', 'voice']):
        return 'Audio/Speech Processing'
    elif any(term in combined for term in ['multimodal', 'cross', 'fusion']):
        return 'Multimodal AI'
    elif any(term in combined for term in ['theory', 'optimization', 'learning']):
        return 'ML Theory & Methods'
    else:
        return f'Specialized Domain ({keywords[0]})'
```

#### 1.3 Extract Relevant Venues (30 minutes)
```python
def extract_venues_detailed(mila_papers, domain_analysis):
    """Extract venues with domain context"""
    
    venue_analysis = {
        'all_venues': {},
        'venues_by_domain': {},
        'venue_importance': {}
    }
    
    # Overall venue analysis
    venue_counts = mila_papers['venue'].value_counts()
    
    # Filter for significant venues (minimum 2 papers over 6 years)
    significant_venues = venue_counts[venue_counts >= 2]
    
    # Categorize venues by domain
    for domain_id, domain_info in domain_analysis['domains'].items():
        domain_name = domain_analysis['domain_names'][domain_id]
        venue_analysis['venues_by_domain'][domain_name] = list(domain_info['top_venues'].keys())
    
    # Calculate venue importance score
    for venue in significant_venues.index:
        papers_count = significant_venues[venue]
        years_active = len(mila_papers[mila_papers['venue'] == venue]['year'].unique())
        importance_score = papers_count * years_active  # Simple scoring
        
        venue_analysis['venue_importance'][venue] = {
            'papers_count': papers_count,
            'years_active': years_active,
            'importance_score': importance_score
        }
    
    return venue_analysis
```

### Step 2: Universal Paper Collection (4 hours)

#### 2.1 Setup Collection Infrastructure (30 minutes)
```python
def setup_paper_collection():
    """Initialize all APIs and data structures"""
    
    # API setup
    setup_citation_apis()
    
    # Data structures
    collection_results = {
        'raw_papers': [],
        'academic_filtered': [],
        'industry_filtered': [],
        'collection_stats': {},
        'failed_searches': []
    }
    
    # Rate limiting setup
    rate_limits = {
        'google_scholar': 1.0,  # 1 second between requests
        'semantic_scholar': 0.1,  # 100ms between requests
        'retry_attempts': 3
    }
    
    return collection_results, rate_limits

def setup_organization_lists():
    """Setup sanity check lists for academic and industry organizations"""
    
    expected_academic_orgs = [
        # Top US Universities
        'MIT', 'Stanford University', 'Carnegie Mellon', 'UC Berkeley',
        'Harvard', 'Princeton', 'Yale', 'University of Washington',
        'NYU', 'Columbia', 'University of Chicago', 'Caltech',
        
        # Top International Universities  
        'University of Oxford', 'University of Cambridge', 'ETH Zurich',
        'University of Toronto', 'McGill University', 'EPFL',
        'Technical University of Munich', 'University College London',
        
        # Research Institutes
        'Max Planck Institute', 'Allen Institute', 'Mila', 'Vector Institute'
    ]
    
    expected_industry_orgs = [
        # Big Tech AI Labs
        'Google', 'Google Research', 'Google DeepMind', 'DeepMind',
        'OpenAI', 'Microsoft', 'Microsoft Research', 'Meta', 'Facebook',
        'Apple', 'Amazon', 'NVIDIA', 'Intel',
        
        # AI-focused Companies
        'Anthropic', 'Cohere', 'Hugging Face', 'Stability AI',
        'Character.AI', 'Adept', 'Inflection AI',
        
        # Research-oriented Industry
        'IBM Research', 'Adobe Research', 'Salesforce Research'
    ]
    
    return expected_academic_orgs, expected_industry_orgs
```

#### 2.2 Core Paper Collection Function (2.5 hours)
```python
def collect_papers_universal(domain_analysis, venue_analysis, target_per_domain_year=8):
    """Universal paper collection for both academic and industry"""
    
    collection_results = {
        'all_papers': [],
        'collection_stats': defaultdict(lambda: defaultdict(int))
    }
    
    # Collect from each domain and year
    for domain_id, domain_info in domain_analysis['domains'].items():
        domain_name = domain_analysis['domain_names'][domain_id]
        
        for year in range(2019, 2025):
            print(f"Collecting {domain_name} papers for {year}...")
            
            # Get relevant venues for this domain
            domain_venues = venue_analysis['venues_by_domain'].get(domain_name, [])
            
            year_papers = []
            
            # Collect from domain-specific venues
            for venue in domain_venues[:5]:  # Top 5 venues per domain
                venue_papers = collect_from_venue_year(venue, year, domain_name)
                year_papers.extend(venue_papers)
            
            # Also collect from major ML venues with domain keywords
            major_venues = ['NeurIPS', 'ICML', 'ICLR']
            for venue in major_venues:
                venue_papers = collect_from_venue_year_with_keywords(
                    venue, year, domain_info['keywords'][:5], domain_name
                )
                year_papers.extend(venue_papers)
            
            # Remove duplicates and sort by citations
            year_papers = deduplicate_papers(year_papers)
            year_papers = sorted(year_papers, key=lambda x: x.get('citations', 0), reverse=True)
            
            # Take top papers for this domain/year
            selected_papers = year_papers[:target_per_domain_year]
            
            # Add metadata
            for paper in selected_papers:
                paper['mila_domain'] = domain_name
                paper['collection_year'] = year
                paper['selection_reason'] = 'domain_venue_match'
            
            collection_results['all_papers'].extend(selected_papers)
            collection_results['collection_stats'][domain_name][year] = len(selected_papers)
            
            print(f"  Collected {len(selected_papers)} papers for {domain_name} {year}")
    
    return collection_results

def collect_from_venue_year(venue, year, domain_name, min_citations=None):
    """Collect papers from specific venue and year"""
    
    if min_citations is None:
        # Dynamic citation threshold based on year
        min_citations = max(10, 100 - (2024 - year) * 15)  # More recent = lower threshold
    
    papers = []
    
    # Method 1: Google Scholar
    try:
        papers_gs = search_google_scholar(venue, year, min_citations)
        papers.extend(papers_gs)
        time.sleep(1)  # Rate limiting
    except Exception as e:
        print(f"    Google Scholar failed for {venue} {year}: {e}")
    
    # Method 2: Semantic Scholar
    try:
        papers_ss = search_semantic_scholar(venue, year, min_citations)
        papers.extend(papers_ss)
        time.sleep(0.1)  # Rate limiting
    except Exception as e:
        print(f"    Semantic Scholar failed for {venue} {year}: {e}")
    
    # Add collection metadata
    for paper in papers:
        paper['collection_venue'] = venue
        paper['collection_method'] = 'venue_search'
        paper['domain_context'] = domain_name
    
    return papers

def search_google_scholar(venue, year, min_citations):
    """Search Google Scholar for venue/year papers"""
    
    papers = []
    
    # Construct search query
    if venue in ['NeurIPS', 'ICML', 'ICLR']:
        # These venues have specific search patterns
        search_query = f'source:"{venue}" year:{year}'
    else:
        search_query = f'venue:"{venue}" year:{year}'
    
    try:
        search_results = scholarly.search_pubs(search_query)
        
        for i, paper in enumerate(search_results):
            if i >= 50:  # Limit to avoid timeouts
                break
            
            citations = paper.get('num_citations', 0)
            if citations >= min_citations:
                
                # Extract author information
                authors_info = []
                for author in paper.get('author', []):
                    author_data = {
                        'name': author.get('name', ''),
                        'affiliation': author.get('affiliation', ''),
                        'scholar_id': author.get('scholar_id', '')
                    }
                    authors_info.append(author_data)
                
                paper_data = {
                    'title': paper.get('title', ''),
                    'authors': authors_info,
                    'venue': venue,
                    'year': year,
                    'citations': citations,
                    'abstract': paper.get('abstract', ''),
                    'url': paper.get('url', ''),
                    'scholar_id': paper.get('scholar_id', ''),
                    'source': 'google_scholar'
                }
                
                papers.append(paper_data)
    
    except Exception as e:
        print(f"      Google Scholar search failed: {e}")
    
    return papers

def search_semantic_scholar(venue, year, min_citations):
    """Search Semantic Scholar for venue/year papers"""
    
    papers = []
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    params = {
        'query': f'venue:"{venue}" year:{year}',
        'limit': 100,
        'fields': 'title,authors,venue,year,citationCount,abstract,url,paperId'
    }
    
    try:
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            for paper in data.get('data', []):
                citations = paper.get('citationCount', 0)
                
                if citations >= min_citations:
                    # Process author information
                    authors_info = []
                    for author in paper.get('authors', []):
                        author_data = {
                            'name': author.get('name', ''),
                            'affiliation': '',  # Semantic Scholar doesn't always have this
                            'author_id': author.get('authorId', '')
                        }
                        authors_info.append(author_data)
                    
                    paper_data = {
                        'title': paper.get('title', ''),
                        'authors': authors_info,
                        'venue': paper.get('venue', venue),
                        'year': paper.get('year', year),
                        'citations': citations,
                        'abstract': paper.get('abstract', ''),
                        'url': paper.get('url', ''),
                        'semantic_id': paper.get('paperId', ''),
                        'source': 'semantic_scholar'
                    }
                    
                    papers.append(paper_data)
        
        else:
            print(f"      Semantic Scholar API error: {response.status_code}")
    
    except Exception as e:
        print(f"      Semantic Scholar search failed: {e}")
    
    return papers
```

#### 2.3 Deduplication and Quality Control (1 hour)
```python
def deduplicate_papers(papers):
    """Remove duplicate papers across sources"""
    
    seen_papers = {}
    deduplicated = []
    
    for paper in papers:
        # Create a normalized title for comparison
        title_norm = normalize_title(paper.get('title', ''))
        
        if title_norm not in seen_papers:
            seen_papers[title_norm] = paper
            deduplicated.append(paper)
        else:
            # Merge information from duplicate
            existing = seen_papers[title_norm]
            merged = merge_paper_info(existing, paper)
            seen_papers[title_norm] = merged
    
    return list(seen_papers.values())

def normalize_title(title):
    """Normalize title for deduplication"""
    import re
    
    if not title:
        return ""
    
    # Convert to lowercase
    title_norm = title.lower()
    
    # Remove punctuation and extra spaces
    title_norm = re.sub(r'[^\w\s]', ' ', title_norm)
    title_norm = re.sub(r'\s+', ' ', title_norm).strip()
    
    return title_norm

def merge_paper_info(paper1, paper2):
    """Merge information from two versions of the same paper"""
    
    merged = paper1.copy()
    
    # Prefer Google Scholar citations if available
    if paper2.get('source') == 'google_scholar' and paper2.get('citations'):
        merged['citations'] = paper2['citations']
        merged['citations_source'] = 'google_scholar'
    
    # Merge author information
    if paper2.get('authors') and not merged.get('authors'):
        merged['authors'] = paper2['authors']
    
    # Collect all sources
    sources = [merged.get('source', '')]
    if paper2.get('source'):
        sources.append(paper2['source'])
    merged['all_sources'] = list(set(sources))
    
    return merged
```

### Step 3: Academic vs Industry Filtering (1.5 hours)

#### 3.1 Enhanced Author Affiliation Analysis (45 minutes)
```python
def classify_all_papers(papers):
    """Classify all papers as academic or industry eligible"""
    
    classification_results = {
        'academic_eligible': [],
        'industry_eligible': [],
        'needs_manual_review': [],
        'classification_stats': {}
    }
    
    academic_orgs, industry_orgs = setup_organization_lists()
    
    for paper in papers:
        classification = classify_paper_authorship(paper, academic_orgs, industry_orgs)
        
        if classification['category'] == 'academic_eligible':
            classification_results['academic_eligible'].append(paper)
        elif classification['category'] == 'industry_eligible':
            classification_results['industry_eligible'].append(paper)
        else:
            classification_results['needs_manual_review'].append(paper)
        
        # Store classification details in paper
        paper['authorship_analysis'] = classification
    
    return classification_results

def classify_paper_authorship(paper, academic_orgs, industry_orgs):
    """Detailed authorship classification"""
    
    authors = paper.get('authors', [])
    
    if not authors:
        return {
            'category': 'needs_manual_review',
            'reason': 'no_author_info',
            'confidence': 0.0
        }
    
    academic_count = 0
    industry_count = 0
    unknown_count = 0
    
    author_details = []
    
    for author in authors:
        affiliation = author.get('affiliation', '')
        
        if not affiliation:
            # Try to get affiliation from author name patterns
            affiliation = infer_affiliation_from_name(author.get('name', ''))
        
        affiliation_type = classify_detailed_affiliation(affiliation, academic_orgs, industry_orgs)
        
        author_details.append({
            'name': author.get('name', ''),
            'affiliation': affiliation,
            'type': affiliation_type['type'],
            'confidence': affiliation_type['confidence']
        })
        
        if affiliation_type['type'] == 'academic':
            academic_count += 1
        elif affiliation_type['type'] == 'industry':
            industry_count += 1
        else:
            unknown_count += 1
    
    total_classified = academic_count + industry_count
    
    if total_classified == 0:
        return {
            'category': 'needs_manual_review',
            'reason': 'all_unknown_affiliations',
            'author_details': author_details,
            'confidence': 0.0
        }
    
    industry_percentage = industry_count / total_classified
    academic_percentage = academic_count / total_classified
    
    # Classification logic
    if industry_percentage < 0.25:  # <25% industry = academic eligible
        category = 'academic_eligible'
        confidence = academic_percentage
    elif academic_percentage < 0.25:  # <25% academic = industry eligible
        category = 'industry_eligible'
        confidence = industry_percentage
    else:
        category = 'needs_manual_review'
        confidence = 0.5
    
    return {
        'category': category,
        'academic_count': academic_count,
        'industry_count': industry_count,
        'unknown_count': unknown_count,
        'industry_percentage': industry_percentage,
        'academic_percentage': academic_percentage,
        'confidence': confidence,
        'author_details': author_details
    }

def classify_detailed_affiliation(affiliation, academic_orgs, industry_orgs):
    """Enhanced affiliation classification with confidence scores"""
    
    if not affiliation:
        return {'type': 'unknown', 'confidence': 0.0}
    
    affiliation_lower = affiliation.lower()
    
    # Check for exact matches first (high confidence)
    for org in academic_orgs:
        if org.lower() in affiliation_lower:
            return {'type': 'academic', 'confidence': 0.9}
    
    for org in industry_orgs:
        if org.lower() in affiliation_lower:
            return {'type': 'industry', 'confidence': 0.9}
    
    # Check for keyword patterns (medium confidence)
    academic_keywords = [
        'university', 'institut', 'college', 'school', 'research center',
        'laboratory', 'academia', 'department of', 'faculty of'
    ]
    
    industry_keywords = [
        'corporation', 'inc.', 'ltd.', 'llc', 'labs', 'research lab',
        'ai lab', 'technologies'
    ]
    
    academic_matches = sum(1 for keyword in academic_keywords if keyword in affiliation_lower)
    industry_matches = sum(1 for keyword in industry_keywords if keyword in affiliation_lower)
    
    if academic_matches > industry_matches and academic_matches > 0:
        return {'type': 'academic', 'confidence': 0.7}
    elif industry_matches > academic_matches and industry_matches > 0:
        return {'type': 'industry', 'confidence': 0.7}
    
    return {'type': 'unknown', 'confidence': 0.0}
```

#### 3.2 Final Paper Selection (45 minutes)
```python
def select_final_papers(classification_results, target_per_domain_year=5):
    """Select final papers for academic and industry benchmarks"""
    
    final_selection = {
        'academic_benchmarks': [],
        'industry_benchmarks': [],
        'selection_stats': {}
    }
    
    # Group papers by domain and year for balanced selection
    academic_by_domain_year = group_papers_by_domain_year(
        classification_results['academic_eligible']
    )
    
    industry_by_domain_year = group_papers_by_domain_year(
        classification_results['industry_eligible']
    )
    
    # Select academic benchmarks
    for (domain, year), papers in academic_by_domain_year.items():
        # Sort by citations and select top papers
        sorted_papers = sorted(papers, key=lambda x: x.get('citations', 0), reverse=True)
        selected = sorted_papers[:target_per_domain_year]
        
        for paper in selected:
            paper['benchmark_type'] = 'academic'
            paper['selection_rank'] = sorted_papers.index(paper) + 1
        
        final_selection['academic_benchmarks'].extend(selected)
    
    # Select industry benchmarks
    for (domain, year), papers in industry_by_domain_year.items():
        sorted_papers = sorted(papers, key=lambda x: x.get('citations', 0), reverse=True)
        selected = sorted_papers[:target_per_domain_year]
        
        for paper in selected:
            paper['benchmark_type'] = 'industry'
            paper['selection_rank'] = sorted_papers.index(paper) + 1
        
        final_selection['industry_benchmarks'].extend(selected)
    
    return final_selection

def group_papers_by_domain_year(papers):
    """Group papers by domain and year for balanced selection"""
    
    grouped = defaultdict(list)
    
    for paper in papers:
        domain = paper.get('mila_domain', 'Unknown')
        year = paper.get('collection_year', paper.get('year', 0))
        grouped[(domain, year)].append(paper)
    
    return grouped
```

### Step 4: Quality Control and Validation (1 hour)

#### 4.1 Sanity Check Implementation (30 minutes)
```python
def perform_sanity_checks(final_selection, expected_academic_orgs, expected_industry_orgs):
    """Comprehensive sanity checks on final selection"""
    
    sanity_results = {
        'academic_org_coverage': {},
        'industry_org_coverage': {},
        'domain_balance': {},
        'temporal_balance': {},
        'citation_distribution': {},
        'quality_flags': []
    }
    
    # Check academic organization representation
    academic_papers = final_selection['academic_benchmarks']
    found_academic_orgs = set()
    
    for paper in academic_papers:
        for author in paper.get('authors', []):
            affiliation = author.get('affiliation', '').lower()
            for org in expected_academic_orgs:
                if org.lower() in affiliation:
                    found_academic_orgs.add(org)
    
    missing_academic_orgs = set(expected_academic_orgs) - found_academic_orgs
    sanity_results['academic_org_coverage'] = {
        'found': list(found_academic_orgs),
        'missing': list(missing_academic_orgs),
        'coverage_percentage': len(found_academic_orgs) / len(expected_academic_orgs)
    }
    
    # Check industry organization representation
    industry_papers = final_selection['industry_benchmarks']
    found_industry_orgs = set()
    
    for paper in industry_papers:
        for author in paper.get('authors', []):
            affiliation = author.get('affiliation', '').lower()
            for org in expected_industry_orgs:
                if org.lower() in affiliation:
                    found_industry_orgs.add(org)
    
    missing_industry_orgs = set(expected_industry_orgs) - found_industry_orgs
    sanity_results['industry_org_coverage'] = {
        'found': list(found_industry_orgs),
        'missing': list(missing_industry_orgs),
        'coverage_percentage': len(found_industry_orgs) / len(expected_industry_orgs)
    }
    
    # Flag potential issues
    if sanity_results['academic_org_coverage']['coverage_percentage'] < 0.3:
        sanity_results['quality_flags'].append('low_academic_org_coverage')
    
    if sanity_results['industry_org_coverage']['coverage_percentage'] < 0.2:
        sanity_results['quality_flags'].append('low_industry_org_coverage')
    
    return sanity_results

def generate_collection_report(final_selection, sanity_results, domain_analysis):
    """Generate comprehensive collection report"""
    
    report = {
        'summary': {},
        'domain_distribution': {},
        'temporal_distribution': {},
        'quality_assessment': {},
        'recommendations': []
    }
    
    # Summary statistics
    academic_count = len(final_selection['academic_benchmarks'])
    industry_count = len(final_selection['industry_benchmarks'])
    
    report['summary'] = {
        'total_papers': academic_count + industry_count,
        'academic_papers': academic_count,
        'industry_papers': industry_count,
        'domains_covered': len(domain_analysis['domain_names']),
        'years_covered': 6  # 2019-2024
    }
    
    # Domain distribution
    for domain_name in domain_analysis['domain_names'].values():
        academic_domain_count = len([p for p in final_selection['academic_benchmarks'] 
                                   if p.get('mila_domain') == domain_name])
        industry_domain_count = len([p for p in final_selection['industry_benchmarks'] 
                                   if p.get('mila_domain') == domain_name])
        
        report['domain_distribution'][domain_name] = {
            'academic': academic_domain_count,
            'industry': industry_domain_count,
            'total': academic_domain_count + industry_domain_count
        }
    
    # Quality recommendations
    if sanity_results['academic_org_coverage']['coverage_percentage'] < 0.5:
        report['recommendations'].append('Consider manual addition of papers from missing academic institutions')
    
    if any('unknown' in p.get('authorship_analysis', {}).get('category', '') 
           for p in final_selection['academic_benchmarks'] + final_selection['industry_benchmarks']):
        report['recommendations'].append('Manual review needed for papers with unknown author affiliations')
    
    return report
```

## Implementation Timeline

### Detailed Hour-by-Hour Schedule
```
Hour 1: Mila corpus loading and initial analysis
Hour 2-2.5: Domain extraction and clustering 
Hour 2.5-3: Venue analysis and categorization
Hour 3-4: Paper collection infrastructure setup
Hour 4-6.5: Universal paper collection (all domains/years)
Hour 6.5-7.5: Deduplication and initial quality control
Hour 7.5-8.5: Author affiliation classification 
Hour 8.5-9: Final paper selection and balancing
Hour 9-10: Sanity checks and report generation
```

## Expected Deliverables
- **360-720 total papers** (5-10 per domain per year, academic + industry)
- **Mila-derived domain classification** (6-10 research domains)
- **Venue analysis** with domain mapping
- **Quality validation report** with sanity check results
- **Author affiliation analysis** with confidence scores

## Success Metrics
- **Collection coverage**: 5-10 papers per domain per year
- **Citation verification**: 100% papers with validated citations
- **Organization coverage**: >30% expected academic orgs, >20% expected industry orgs
- **Quality flags**: <15% papers needing manual review

Ready to implement this detailed plan?