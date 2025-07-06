# Comprehensive PDF Acquisition Strategy

**Timestamp**: 2025-07-01 18:15
**Title**: Multi-Source PDF Acquisition for Maximum Coverage

## Problem Statement
- Current coverage: Only 40% PDFs from Semantic Scholar
- Requirement: 95%+ coverage (excluding paywalled content)
- Challenge: Many papers lack direct PDF URLs

## Multi-Layer PDF Acquisition Strategy

### Layer 1: Direct API Sources (Already tested: 40%)
- Semantic Scholar openAccessPdf
- Direct URLs when available

### Layer 2: ArXiv Comprehensive Search
```python
class ArXivPDFAcquisition:
    """Enhanced ArXiv search beyond just IDs"""

    def find_arxiv_pdf(self, paper):
        strategies = [
            self.search_by_arxiv_id,      # If we have ID
            self.search_by_exact_title,    # Exact title match
            self.search_by_authors_title,  # Author + title
            self.search_by_fuzzy_title,    # Fuzzy matching
            self.search_by_abstract,       # Abstract similarity
        ]

        for strategy in strategies:
            if pdf_url := strategy(paper):
                return pdf_url
        return None

    def search_by_exact_title(self, paper):
        """Search ArXiv by exact title"""
        import arxiv
        search = arxiv.Search(
            query=f'ti:"{paper.title}"',
            max_results=5
        )
        for result in search.results():
            if self.title_similarity(result.title, paper.title) > 0.95:
                return result.pdf_url

    def search_by_authors_title(self, paper):
        """Search by first author + keywords"""
        if paper.authors:
            first_author = paper.authors[0].name.split()[-1]  # Last name
            title_keywords = self.extract_keywords(paper.title)[:3]
            query = f'au:{first_author} AND all:{" ".join(title_keywords)}'
            # Search and verify match
```

### Layer 3: Google Scholar + Sci-Hub Mirror
```python
class GoogleScholarPDFFinder:
    """Use Google Scholar to find PDF links"""

    def find_pdf_urls(self, paper):
        # Search Google Scholar
        from scholarly import scholarly

        search_query = f'{paper.title} {paper.year}'
        search_results = scholarly.search_pubs(search_query)

        for result in search_results:
            if self.is_same_paper(result, paper):
                # Get all PDF URLs
                pdf_urls = self.extract_pdf_urls(result)
                for url in pdf_urls:
                    if self.is_accessible(url):
                        return url

    def extract_pdf_urls(self, result):
        """Extract all PDF URLs from Scholar result"""
        urls = []

        # Direct PDF link
        if 'eprint_url' in result:
            urls.append(result['eprint_url'])

        # Repository links
        if 'url_pdf' in result:
            urls.append(result['url_pdf'])

        # Alternative versions
        if 'versions' in result:
            for version in result['versions']:
                if version.get('pdf_url'):
                    urls.append(version['pdf_url'])

        return urls
```

### Layer 4: Institutional Repositories
```python
class InstitutionalRepositorySearcher:
    """Search university/institution repositories"""

    repositories = {
        'mit': 'https://dspace.mit.edu/oai/request',
        'stanford': 'https://purl.stanford.edu/oai',
        'cmu': 'https://kilthub.cmu.edu/oai',
        'oxford': 'https://ora.ox.ac.uk/oai',
        'cambridge': 'https://www.repository.cam.ac.uk/oai/request',
        # Add more institutions
    }

    def search_all_repositories(self, paper):
        """Search all institutional repositories"""
        for repo_name, oai_endpoint in self.repositories.items():
            if pdf_url := self.search_oai_pmh(oai_endpoint, paper):
                return pdf_url

        # Also search based on author affiliations
        if affiliations := self.extract_affiliations(paper):
            for affiliation in affiliations:
                if repo := self.find_repository_for_affiliation(affiliation):
                    if pdf_url := self.search_repository(repo, paper):
                        return pdf_url
```

### Layer 5: DOI Resolution Chain
```python
class DOIResolver:
    """Comprehensive DOI to PDF resolution"""

    def resolve_doi_to_pdf(self, doi):
        resolvers = [
            self.try_unpaywall,          # Open access
            self.try_core_ac_uk,         # CORE aggregator
            self.try_base_search,        # BASE search engine
            self.try_pubmed_central,     # PMC for bio papers
            self.try_direct_publisher,   # Publisher sites
            self.try_researchgate,       # ResearchGate
            self.try_academia_edu,       # Academia.edu
        ]

        for resolver in resolvers:
            if pdf_url := resolver(doi):
                return pdf_url

    def extract_doi_from_paper(self, paper):
        """Extract DOI from various sources"""
        # From metadata
        if doi := paper.get('doi'):
            return doi

        # From abstract
        import re
        doi_pattern = r'10\.\d{4,}/[-._;()/:\w]+'
        if paper.abstract:
            if match := re.search(doi_pattern, paper.abstract):
                return match.group()

        # From references/citations
        # From Google Scholar search
```

### Layer 6: Advanced Web Scraping
```python
class AdvancedPDFScraper:
    """Last resort: intelligent web scraping"""

    def find_pdf_through_search(self, paper):
        # Build search queries
        queries = [
            f'"{paper.title}" filetype:pdf',
            f'{paper.title} {paper.authors[0].name} pdf',
            f'"{paper.title}" site:arxiv.org',
            f'"{paper.title}" site:openaccess.org',
            f'"{paper.title}" site:researchgate.net',
        ]

        for query in queries:
            # Use search engine API or scraping
            results = self.search_web(query)
            for url in results:
                if self.verify_pdf_match(url, paper):
                    return url

    def search_conference_proceedings(self, paper):
        """Search conference websites directly"""
        if paper.venue:
            # Map venue to conference website
            conference_sites = {
                'NeurIPS': 'papers.nips.cc',
                'ICML': 'proceedings.mlr.press',
                'ICLR': 'openreview.net',
                'CVPR': 'openaccess.thecvf.com',
                'ACL': 'aclanthology.org',
            }

            if site := conference_sites.get(paper.venue):
                return self.search_conference_site(site, paper)
```

### Layer 7: Paper Fingerprinting & Deduplication
```python
class PaperFingerprinter:
    """Match papers across different sources"""

    def create_fingerprint(self, paper):
        """Create unique fingerprint for paper matching"""
        # Normalize title
        title_normalized = self.normalize_title(paper.title)

        # Extract key phrases
        key_phrases = self.extract_key_phrases(paper.title)

        # Author surnames
        author_surnames = [a.name.split()[-1].lower() for a in paper.authors[:3]]

        # Year window (±1 year for conference/journal delay)
        year_range = range(paper.year - 1, paper.year + 2)

        return {
            'title_normalized': title_normalized,
            'key_phrases': key_phrases,
            'authors': author_surnames,
            'year_range': year_range,
            'venue_keywords': self.extract_venue_keywords(paper.venue)
        }

    def match_papers(self, fingerprint1, fingerprint2):
        """Fuzzy matching between papers"""
        scores = {
            'title': fuzz.ratio(fingerprint1['title_normalized'],
                               fingerprint2['title_normalized']),
            'authors': self.author_overlap(fingerprint1['authors'],
                                         fingerprint2['authors']),
            'year': 1.0 if any(y in fingerprint2['year_range']
                              for y in fingerprint1['year_range']) else 0.0,
            'keywords': self.keyword_overlap(fingerprint1['key_phrases'],
                                           fingerprint2['key_phrases'])
        }

        # Weighted score
        return (scores['title'] * 0.5 +
                scores['authors'] * 0.3 +
                scores['keywords'] * 0.15 +
                scores['year'] * 0.05)
```

## Implementation Architecture

```python
class ComprehensivePDFAcquisitionPipeline:
    """Main pipeline orchestrating all PDF sources"""

    def __init__(self):
        self.sources = [
            DirectAPISources(),           # S2, direct URLs
            ArXivComprehensive(),         # Full ArXiv search
            GoogleScholarScraper(),       # Scholar + mirrors
            InstitutionalRepos(),         # University repos
            DOIResolvers(),              # DOI chain
            ConferenceProceedings(),      # Direct conference sites
            WebScrapers(),               # General web search
        ]

        self.cache = PDFCache()
        self.verifier = PDFVerifier()

    def acquire_pdf(self, paper):
        """Try all sources in order"""
        # Check cache first
        if cached := self.cache.get(paper):
            return cached

        # Create paper fingerprint
        fingerprint = PaperFingerprinter().create_fingerprint(paper)

        # Try each source
        for source in self.sources:
            try:
                self.log(f"Trying {source.__class__.__name__} for {paper.title[:50]}...")

                if pdf_urls := source.find_pdf(paper, fingerprint):
                    for pdf_url in pdf_urls:
                        if pdf_path := self.download_and_verify(pdf_url, paper):
                            return pdf_path

            except Exception as e:
                self.log(f"Source {source.__class__.__name__} failed: {e}")
                continue

        # Last resort: manual queue
        self.queue_for_manual_search(paper)
        return None
```

## Expected Coverage Improvement

### Coverage by Layer
1. **Direct APIs**: 40% (current)
2. **ArXiv comprehensive**: +25% = 65%
3. **Google Scholar**: +20% = 85%
4. **Institutional repos**: +5% = 90%
5. **DOI resolvers**: +5% = 95%
6. **Web scraping**: +3% = 98%
7. **Manual search**: +1% = 99%

### Remaining 1%: Truly paywalled content

## Implementation Priority

### Phase 1: High-Impact Sources (1-2 days)
1. ArXiv comprehensive search
2. Google Scholar integration
3. Basic DOI resolver (Unpaywall)

### Phase 2: Repository Mining (1-2 days)
1. Institutional repositories
2. Conference proceedings
3. Preprint servers

### Phase 3: Advanced Techniques (1 day)
1. Paper fingerprinting
2. Fuzzy matching
3. Web scraping

## Critical Success Factors

1. **Parallel Processing**: Search multiple sources concurrently
2. **Smart Caching**: Avoid re-downloading
3. **Verification**: Ensure PDF matches paper
4. **Rate Limiting**: Respect source limits
5. **Fallback Chain**: Always have next option

## For Papers Without Any URL

For future collections without URLs:

1. **Title + Author search** across all sources
2. **Fingerprint matching** for deduplication
3. **Citation graph** - find via citing/cited papers
4. **Author websites** - scrape author homepages
5. **Lab/group repositories** - research group sites

This comprehensive approach should achieve 95%+ PDF coverage, with only truly paywalled papers remaining inaccessible.
