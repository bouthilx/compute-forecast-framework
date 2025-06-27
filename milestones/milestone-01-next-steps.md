# Milestone 1: Immediate Next Steps

## Step 1: Environment Setup (30 minutes)

### 1.1 Install Required Libraries
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core libraries
pip install pandas numpy scipy scikit-learn
pip install scholarly requests beautifulsoup4
pip install matplotlib seaborn plotly
pip install jupyter ipykernel

# Optional: For faster processing
pip install tqdm joblib
```

### 1.2 Verify API Access
```python
# Test Google Scholar access
from scholarly import scholarly
import requests
import time

def test_apis():
    """Test API connectivity and basic functionality"""
    
    # Test Google Scholar
    try:
        search_query = "machine learning"
        search_results = scholarly.search_pubs(search_query)
        first_paper = next(search_results)
        print("✅ Google Scholar working:", first_paper.get('title', 'No title'))
    except Exception as e:
        print("❌ Google Scholar failed:", e)
    
    # Test Semantic Scholar
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {'query': 'machine learning', 'limit': 1}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("✅ Semantic Scholar working")
        else:
            print("❌ Semantic Scholar failed:", response.status_code)
    except Exception as e:
        print("❌ Semantic Scholar failed:", e)

# Run the test
test_apis()
```

## Step 2: Mila Data Preparation (1 hour)

### 2.1 Define Expected Mila Data Format
```python
# Create template/example of expected Mila data structure
import pandas as pd

def create_mila_data_template():
    """Create template showing expected Mila data format"""
    
    template_data = {
        'title': [
            'Attention Is All You Need',
            'BERT: Pre-training of Deep Bidirectional Transformers',
            'Generative Adversarial Networks'
        ],
        'authors': [
            'Ashish Vaswani, Noam Shazeer, Niki Parmar',
            'Jacob Devlin, Ming-Wei Chang, Kenton Lee',
            'Ian Goodfellow, Jean Pouget-Abadie, Mehdi Mirza'
        ],
        'venue': [
            'NeurIPS',
            'NAACL',
            'NeurIPS'
        ],
        'year': [2017, 2019, 2014],
        'abstract': [
            'The dominant sequence transduction models...',
            'We introduce a new language representation model...',
            'We propose a new framework for estimating generative models...'
        ],
        'doi': [
            '10.5555/3295222.3295349',
            '10.18653/v1/N19-1423',
            '10.5555/2969033.2969125'
        ]
    }
    
    df = pd.DataFrame(template_data)
    df.to_csv('mila_papers_template.csv', index=False)
    
    print("Template created: mila_papers_template.csv")
    print("Required columns:", df.columns.tolist())
    print("Expected format:")
    print(df.head())
    
    return df

# Create the template
template = create_mila_data_template()
```

### 2.2 Verify Mila Data Access
```python
def verify_mila_data():
    """Check if Mila data is available and properly formatted"""
    
    # Try to load Mila data
    try:
        # Replace with actual Mila data path
        mila_data_path = 'mila_papers_2019_2024.csv'
        mila_papers = pd.read_csv(mila_data_path)
        
        print(f"✅ Mila data loaded: {len(mila_papers)} papers")
        print(f"Years: {mila_papers['year'].min()}-{mila_papers['year'].max()}")
        print(f"Venues: {mila_papers['venue'].nunique()} unique")
        
        return mila_papers
        
    except FileNotFoundError:
        print("❌ Mila data file not found")
        print("Expected file: mila_papers_2019_2024.csv")
        print("Please provide Mila publication data in the template format")
        return None
    except Exception as e:
        print(f"❌ Error loading Mila data: {e}")
        return None

# Check Mila data
mila_data = verify_mila_data()
```

## Step 3: Quick Domain Analysis Test (30 minutes)

### 3.1 Basic Domain Clustering
```python
def quick_domain_analysis(mila_papers):
    """Quick test of domain extraction methodology"""
    
    if mila_papers is None:
        print("Cannot run domain analysis without Mila data")
        return None
    
    # Combine text for analysis
    text_data = []
    for _, paper in mila_papers.iterrows():
        title = str(paper.get('title', ''))
        abstract = str(paper.get('abstract', ''))
        venue = str(paper.get('venue', ''))
        text_data.append(f"{title} {abstract} {venue}")
    
    # Basic TF-IDF
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2
    )
    
    tfidf_matrix = vectorizer.fit_transform(text_data)
    
    # Try 6 clusters initially
    kmeans = KMeans(n_clusters=6, random_state=42)
    clusters = kmeans.fit_predict(tfidf_matrix)
    
    # Analyze results
    feature_names = vectorizer.get_feature_names_out()
    
    print("DOMAIN CLUSTERING RESULTS:")
    print("="*50)
    
    for i in range(6):
        papers_in_cluster = (clusters == i).sum()
        
        # Get top keywords
        center = kmeans.cluster_centers_[i]
        top_indices = center.argsort()[-10:][::-1]
        top_keywords = [feature_names[idx] for idx in top_indices]
        
        print(f"\nCluster {i}: {papers_in_cluster} papers")
        print(f"Keywords: {', '.join(top_keywords[:5])}")
        
        # Show example papers
        cluster_papers = mila_papers[clusters == i]['title'].head(3)
        for title in cluster_papers:
            print(f"  - {title}")
    
    return clusters, vectorizer, kmeans

# Run quick test
if mila_data is not None:
    clusters, vectorizer, kmeans = quick_domain_analysis(mila_data)
```

## Step 4: Single Paper Collection Test (30 minutes)

### 4.1 Test Paper Search Function
```python
def test_single_paper_search():
    """Test paper collection for a single venue/year"""
    
    print("Testing paper collection for NeurIPS 2023...")
    
    # Test parameters
    venue = "NeurIPS"
    year = 2023
    min_citations = 5  # Low threshold for testing
    
    papers = []
    
    # Test Google Scholar search
    try:
        print("Testing Google Scholar...")
        search_query = f'venue:"{venue}" year:{year}'
        search_results = scholarly.search_pubs(search_query)
        
        count = 0
        for paper in search_results:
            if count >= 5:  # Just get 5 for testing
                break
                
            citations = paper.get('num_citations', 0)
            if citations >= min_citations:
                paper_data = {
                    'title': paper.get('title', ''),
                    'authors': paper.get('author', []),
                    'venue': venue,
                    'year': year,
                    'citations': citations,
                    'source': 'google_scholar'
                }
                papers.append(paper_data)
                count += 1
                
                print(f"  Found: {paper_data['title'][:50]}... ({citations} citations)")
            
            time.sleep(0.5)  # Rate limiting
            
    except Exception as e:
        print(f"Google Scholar test failed: {e}")
    
    # Test Semantic Scholar
    try:
        print("\nTesting Semantic Scholar...")
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': f'venue:"{venue}" year:{year}',
            'limit': 5,
            'fields': 'title,authors,venue,year,citationCount'
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for paper in data.get('data', []):
                citations = paper.get('citationCount', 0)
                if citations >= min_citations:
                    paper_data = {
                        'title': paper.get('title', ''),
                        'authors': paper.get('authors', []),
                        'venue': paper.get('venue', venue),
                        'year': paper.get('year', year),
                        'citations': citations,
                        'source': 'semantic_scholar'
                    }
                    papers.append(paper_data)
                    print(f"  Found: {paper_data['title'][:50]}... ({citations} citations)")
        else:
            print(f"Semantic Scholar API error: {response.status_code}")
            
    except Exception as e:
        print(f"Semantic Scholar test failed: {e}")
    
    print(f"\nTest completed: Found {len(papers)} papers total")
    return papers

# Run single paper collection test
test_papers = test_single_paper_search()
```

## Step 5: Affiliation Classification Test (30 minutes)

### 5.1 Test Author Classification
```python
def test_affiliation_classification():
    """Test author affiliation classification on sample data"""
    
    # Sample author data for testing
    test_authors = [
        {'name': 'John Smith', 'affiliation': 'Stanford University'},
        {'name': 'Jane Doe', 'affiliation': 'Google Research'},
        {'name': 'Bob Johnson', 'affiliation': 'MIT CSAIL'},
        {'name': 'Alice Brown', 'affiliation': 'Meta AI Research'},
        {'name': 'Charlie Wilson', 'affiliation': 'University of Oxford'},
        {'name': 'Diana Lee', 'affiliation': 'OpenAI'},
        {'name': 'Eve Chen', 'affiliation': 'CMU Machine Learning Department'}
    ]
    
    def classify_test_affiliation(affiliation):
        """Simple classification for testing"""
        
        if not affiliation:
            return 'unknown'
        
        affiliation_lower = affiliation.lower()
        
        academic_keywords = [
            'university', 'institut', 'college', 'school',
            'research center', 'laboratory', 'department'
        ]
        
        industry_keywords = [
            'google', 'meta', 'facebook', 'openai', 'microsoft',
            'apple', 'amazon', 'nvidia', 'research'
        ]
        
        if any(keyword in affiliation_lower for keyword in academic_keywords):
            return 'academic'
        elif any(keyword in affiliation_lower for keyword in industry_keywords):
            return 'industry'
        else:
            return 'unknown'
    
    print("AFFILIATION CLASSIFICATION TEST:")
    print("="*50)
    
    for author in test_authors:
        classification = classify_test_affiliation(author['affiliation'])
        print(f"{author['name']:<15} | {author['affiliation']:<25} | {classification}")
    
    # Test paper classification
    test_paper = {
        'title': 'Test Paper',
        'authors': test_authors
    }
    
    academic_count = sum(1 for a in test_authors 
                        if classify_test_affiliation(a['affiliation']) == 'academic')
    industry_count = sum(1 for a in test_authors 
                        if classify_test_affiliation(a['affiliation']) == 'industry')
    
    total_classified = academic_count + industry_count
    if total_classified > 0:
        industry_percentage = industry_count / total_classified
        
        if industry_percentage < 0.25:
            paper_type = 'academic_eligible'
        else:
            paper_type = 'industry_eligible'
    else:
        paper_type = 'needs_review'
    
    print(f"\nPaper classification: {paper_type}")
    print(f"Academic authors: {academic_count}/{len(test_authors)}")
    print(f"Industry authors: {industry_count}/{len(test_authors)}")
    print(f"Industry percentage: {industry_percentage:.1%}")

# Run affiliation test
test_affiliation_classification()
```

## Step 6: Create Implementation Checklist

### 6.1 Pre-Implementation Checklist
```python
def create_implementation_checklist():
    """Create checklist for full implementation"""
    
    checklist = {
        'Environment Setup': [
            '☐ Python environment created and activated',
            '☐ Required libraries installed',
            '☐ Google Scholar API tested',
            '☐ Semantic Scholar API tested'
        ],
        'Data Preparation': [
            '☐ Mila paper data available and formatted',
            '☐ Data structure validated',
            '☐ Sample domain analysis completed',
            '☐ Venue extraction tested'
        ],
        'Collection Testing': [
            '☐ Single venue/year search tested',
            '☐ Paper deduplication tested',
            '☐ Author affiliation classification tested',
            '☐ Citation cross-validation tested'
        ],
        'Implementation Ready': [
            '☐ All tests passing',
            '☐ Error handling implemented',
            '☐ Rate limiting configured',
            '☐ Output format defined'
        ]
    }
    
    print("MILESTONE 1 IMPLEMENTATION CHECKLIST:")
    print("="*60)
    
    for category, items in checklist.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  {item}")
    
    return checklist

# Create checklist
checklist = create_implementation_checklist()
```

## Immediate Action Items (Today)

### Priority 1: Environment Setup (Next 30 minutes)
1. **Install libraries**: Run the pip install commands above
2. **Test APIs**: Execute the API test functions
3. **Verify connectivity**: Ensure Google Scholar and Semantic Scholar work

### Priority 2: Data Access (Next 1 hour)  
1. **Locate Mila data**: Find/obtain the Mila publication dataset
2. **Format verification**: Ensure data matches expected template
3. **Quick analysis**: Run the domain clustering test

### Priority 3: Function Testing (Next 1 hour)
1. **Paper search test**: Run single venue/year collection
2. **Affiliation test**: Verify author classification works
3. **Error handling**: Test what happens when searches fail

## Decision Points

### If Mila Data Not Available:
- **Option A**: Create synthetic test data to develop methodology
- **Option B**: Use publicly available academic publication data
- **Option C**: Start with manual curation of known papers

### If API Access Fails:
- **Option A**: Implement retry mechanisms and proxies
- **Option B**: Focus on manual curation initially
- **Option C**: Use alternative data sources (ArXiv, DBLP)

### If Tests Reveal Issues:
- **Option A**: Adjust methodology based on test results
- **Option B**: Implement fallback strategies
- **Option C**: Manual intervention for critical gaps

**Next concrete step**: Run the environment setup and API tests above to validate the technical foundation.