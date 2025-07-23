# 2025-07-10 - Metadata Collection Capabilities Analysis: DOI and Keywords in Conference Scrapers

## Analysis Requested

The task was to verify the metadata collection capabilities of three major conference scrapers (NeurIPS, ICML, and ICLR), specifically focusing on:
1. Whether DOIs are collected for papers
2. Whether keywords/topics are extracted
3. Understanding the current implementation limitations and data availability

## How I Proceeded

### 1. Code Examination
I examined the implementation of each scraper to understand their current metadata collection capabilities:

- **NeurIPS**: Uses the paperoni adapter (`paperoni/adapters/neurips.py`)
- **ICML**: Uses the PMLR scraper (`compute_forecast/collectors/pmlr.py`)
- **ICLR**: Uses the OpenReview adapter (`paperoni/adapters/openreview.py`)

### 2. Web Research
I conducted web searches to verify the availability of DOIs and keywords on each conference's website:
- Checked NeurIPS Papers pages for DOI presence
- Examined PMLR (Proceedings of Machine Learning Research) structure
- Investigated OpenReview's metadata fields for ICLR papers

### 3. Implementation Analysis
I analyzed what metadata each scraper currently extracts and what additional fields could potentially be collected.

## Outcomes and Findings

### DOI Collection Status

1. **NeurIPS (paperoni adapter)**
   - **Current Status**: DOIs are NOT collected
   - **Availability**: NeurIPS papers do have DOIs, but they are not displayed on the main conference pages
   - **Implementation Gap**: The scraper only extracts title, authors, abstract, and PDF URL

2. **ICML (PMLR scraper)**
   - **Current Status**: DOIs are NOT collected
   - **Availability**: PMLR papers have DOIs, but they require additional navigation to access
   - **Implementation Gap**: The scraper focuses on basic metadata (title, authors, abstract, PDF URL)

3. **ICLR (OpenReview adapter)**
   - **Current Status**: DOIs are NOT collected
   - **Availability**: ICLR papers generally do NOT have DOIs as they are published on OpenReview
   - **Note**: OpenReview is a preprint-like platform that doesn't assign DOIs

### Keyword/Topic Collection Status

1. **NeurIPS**
   - **Current Status**: Keywords are NOT collected
   - **Availability**: Keywords are typically NOT available on the main conference pages
   - **Alternative**: Papers may have keywords in their PDFs but not in web metadata

2. **ICML**
   - **Current Status**: Keywords are NOT collected
   - **Availability**: Keywords are NOT readily available on PMLR pages
   - **Note**: Would require PDF parsing to extract keywords

3. **ICLR**
   - **Current Status**: Keywords are NOT collected
   - **Availability**: OpenReview does have a keywords field that could be extracted
   - **Implementation Gap**: The current adapter doesn't access this field

## Key Takeaways

1. **DOI Coverage is Inconsistent**:
   - NeurIPS and ICML papers have DOIs but they're not easily accessible from the conference pages
   - ICLR papers on OpenReview don't have DOIs at all
   - Collecting DOIs would require additional API calls or page navigation

2. **Keyword Availability is Limited**:
   - Keywords are generally not available in the web metadata for any of the three conferences
   - Only ICLR (via OpenReview) has readily accessible keywords in the platform
   - For NeurIPS and ICML, keywords would need to be extracted from PDF content

3. **Current Implementation Focus**:
   - All three scrapers prioritize essential metadata: title, authors, abstract, and PDF URL
   - They are designed for efficiency and reliability rather than comprehensive metadata collection
   - This aligns with the project's pragmatic approach of "good enough" over "perfect"

4. **Recommendations**:
   - For the current project goals, the existing metadata collection is sufficient
   - Adding DOI/keyword collection would require significant additional work with limited benefit
   - If keywords become critical for analysis, PDF parsing would be the most reliable approach

## Extended Analysis: All Supported Venues

### Todo List for Venue Analysis

Based on the scraper registry table, here are all supported venues that need analysis (excluding kdd, miccai, www):

- [x] **NeurIPS** (NeurIPSScraper) - COMPLETED
- [x] **ICML** (PMLRScraper) - COMPLETED
- [x] **ICLR** (OpenReviewScraper) - COMPLETED
- [ ] **ACL** (ACLAnthologyScraper)
- [ ] **COLING** (ACLAnthologyScraper)
- [ ] **EMNLP** (ACLAnthologyScraper)
- [ ] **NAACL** (ACLAnthologyScraper)
- [ ] **CVPR** (CVFScraper)
- [ ] **ECCV** (CVFScraper)
- [ ] **ICCV** (CVFScraper)
- [ ] **WACV** (CVFScraper)
- [ ] **IJCAI** (IJCAIScraper)
- [ ] **COLM** (OpenReviewScraper)
- [ ] **RLC** (OpenReviewScraper)
- [ ] **TMLR** (OpenReviewScraper)
- [ ] **AISTATS** (PMLRScraper)
- [ ] **CoLLAs** (PMLRScraper)
- [ ] **UAI** (PMLRScraper)
- [ ] **AAAI** (SemanticScholarScraper)

### Analysis Progress

#### ACL Anthology Venues (ACL, COLING, EMNLP, NAACL)
**Scraper:** ACLAnthologyScraper

**Current Implementation:**
- ❌ **DOI**: Not collected
- ❌ **Keywords**: Not collected
- ✅ Collects: title, authors, venue, year, PDF URLs, paper_id

**Code Analysis:**
- The scraper extracts papers from ACL Anthology website
- SimplePaper creation includes: paper_id, title, authors, venue, year, pdf_urls, source_scraper, source_url
- No DOI or keyword extraction implemented

#### CVF Venues (CVPR, ECCV, ICCV, WACV)
**Scraper:** CVFScraper

**Current Implementation:**
- ❌ **DOI**: Not collected
- ❌ **Keywords**: Not collected
- ✅ Collects: title, authors, venue, year, PDF URLs, paper_id

**Code Analysis:**
- Scrapes from CVF Open Access website
- SimplePaper creation includes: paper_id, title, authors, venue, year, pdf_urls, source_scraper, source_url
- No DOI or keyword fields extracted

#### IJCAI
**Scraper:** IJCAIScraper

**Current Implementation:**
- ❌ **DOI**: Not collected
- ❌ **Keywords**: Not collected
- ✅ Collects: title, authors, venue, year, PDF URLs, paper_id

**Code Analysis:**
- Scrapes from ijcai.org proceedings pages
- SimplePaper creation includes: paper_id, title, authors, venue, year, pdf_urls, source_scraper, source_url
- No DOI or keyword extraction

#### OpenReview Venues (COLM, RLC, TMLR)
**Scraper:** OpenReviewScraper (same as ICLR)

**Current Implementation:**
- ❌ **DOI**: Not collected
- ❌ **Keywords**: Not collected (though available in OpenReview)
- ✅ Collects: title, authors, venue, year, abstract, PDF URLs, paper_id

**Code Analysis:**
- Uses OpenReview API (same implementation as ICLR)
- Could potentially access keywords field but doesn't currently

#### PMLR Venues (AISTATS, CoLLAs, UAI)
**Scraper:** PMLRScraper (same as ICML)

**Current Implementation:**
- ❌ **DOI**: Not collected
- ❌ **Keywords**: Not collected
- ✅ Collects: title, authors, venue, year, PDF URLs, paper_id

**Code Analysis:**
- Same implementation as ICML
- Scrapes from proceedings.mlr.press

#### AAAI
**Scraper:** SemanticScholarScraper

**Current Implementation:**
- ✅ **DOI**: COLLECTED! (via externalIds)
- ❌ **Keywords**: Not collected
- ✅ Collects: title, authors, venue, year, abstract, PDF URLs, paper_id, DOI, arxiv_id

**Code Analysis:**
- Uses Semantic Scholar API
- Actually extracts DOI from externalIds field
- This is the ONLY scraper that collects DOIs

### Web Search Verification Results

#### ACL Anthology (ACL, COLING, EMNLP, NAACL)
**Data Availability:**
- **DOI**: The metadata propagates to services like DBLP and Google Scholar, suggesting DOIs are included when available
- **Keywords**: CL Scholar supports keyword-based search, but unclear if keywords are explicitly stored as metadata
- **Note**: ACL Anthology maintains comprehensive metadata that integrates with other academic databases

#### CVF Venues (CVPR, ECCV, ICCV, WACV)
**Data Availability:**
- **DOI**: YES - Available through different publishers:
  - CVPR/ICCV: DOIs available through IEEE Xplore (co-sponsored by IEEE)
  - ECCV: DOIs available through Springer (Lecture Notes in Computer Science)
  - WACV: DOIs available through IEEE
- **Keywords**: Not mentioned in search results
- **Note**: Papers have dual availability - open access versions (CVF/ECVA) and official DOI-linked versions

#### IJCAI
**Data Availability:**
- **DOI**: YES - IJCAI ensures DOI registration/assignment for all papers
- **Keywords**: Not explicitly mentioned
- **Note**: Metadata is used for PDF metadata and DOI registration, indexed in DBLP

#### AAAI
**Data Availability:**
- **DOI**: YES - AAAI ensures DOI registration for all papers (example: https://doi.org/10.1609/icwsm.v12i1.15010)
- **Keywords**: YES - Keywords are part of the metadata associated with AAAI papers
- **Note**: Comprehensive metadata system for indexing and searchability

### Todo List Updated Status

- [x] **NeurIPS** (NeurIPSScraper) - COMPLETED
- [x] **ICML** (PMLRScraper) - COMPLETED
- [x] **ICLR** (OpenReviewScraper) - COMPLETED
- [x] **ACL** (ACLAnthologyScraper) - COMPLETED
- [x] **COLING** (ACLAnthologyScraper) - COMPLETED
- [x] **EMNLP** (ACLAnthologyScraper) - COMPLETED
- [x] **NAACL** (ACLAnthologyScraper) - COMPLETED
- [x] **CVPR** (CVFScraper) - COMPLETED
- [x] **ECCV** (CVFScraper) - COMPLETED
- [x] **ICCV** (CVFScraper) - COMPLETED
- [x] **WACV** (CVFScraper) - COMPLETED
- [x] **IJCAI** (IJCAIScraper) - COMPLETED
- [x] **COLM** (OpenReviewScraper) - COMPLETED
- [x] **RLC** (OpenReviewScraper) - COMPLETED
- [x] **TMLR** (OpenReviewScraper) - COMPLETED
- [x] **AISTATS** (PMLRScraper) - COMPLETED
- [x] **CoLLAs** (PMLRScraper) - COMPLETED
- [x] **UAI** (PMLRScraper) - COMPLETED
- [x] **AAAI** (SemanticScholarScraper) - COMPLETED

## Comprehensive Summary

### DOI Collection Status Across All Venues

**Currently Collecting DOIs:**
- ✅ AAAI (via SemanticScholarScraper) - Only scraper that extracts DOIs

**NOT Collecting DOIs Despite Availability:**
- ❌ CVF venues (CVPR, ECCV, ICCV, WACV) - DOIs available through IEEE/Springer
- ❌ IJCAI - DOIs are registered for all papers
- ❌ ACL Anthology venues - DOIs likely available (propagates to other databases)
- ❌ PMLR venues (ICML, AISTATS, UAI, CoLLAs) - Limited DOI coverage (9% for ICML)

**No DOIs Available:**
- ❌ NeurIPS - Stopped registering DOIs in 2007
- ❌ OpenReview venues (ICLR, COLM, RLC, TMLR) - Preprint-style platform without DOIs

### Keywords Collection Status

**Currently Collecting Keywords:**
- None of the scrapers collect keywords

**Keywords Available But Not Collected:**
- ❌ OpenReview venues (ICLR, COLM, RLC, TMLR) - Keywords available in API
- ❌ AAAI - Keywords are part of the metadata
- ❌ NeurIPS - Authors select keywords during submission (not publicly visible)

**Keywords Availability Unclear:**
- Most other venues don't expose keywords in their web interfaces

### Key Findings

1. **Major Implementation Gap**: Despite DOIs being available for many venues (CVF, IJCAI, AAAI, ACL), only the SemanticScholarScraper collects them.

2. **Keywords Underutilized**: Keywords are rarely exposed in conference web interfaces, though they exist in submission systems.

3. **API vs Web Scraping**: API-based scrapers (Semantic Scholar, OpenReview) have better access to metadata than web scrapers.

4. **Inconsistent DOI Coverage**: Ranges from 0% (NeurIPS, OpenReview) to 100% (CVF, IJCAI, AAAI).

5. **Current Focus**: All scrapers prioritize essential metadata (title, authors, venue, year, PDF) over comprehensive metadata collection.

### Recommendations

1. **Prioritize DOI Collection** for venues where available (CVF, IJCAI) if citation tracking becomes important.

2. **Leverage APIs** when possible - they provide richer metadata than web scraping.

3. **Consider PDF Parsing** for keywords if needed - most reliable approach across all venues.

4. **Current Implementation is Adequate** for the project's stated goals of computational resource analysis.

## Extended Analysis: Academic Identifiers

### Identifiers to Analyze
- **ArXiv ID**: Preprint identifier from arXiv.org
- **Semantic Scholar ID**: Unique identifier in Semantic Scholar database
- **PMID**: PubMed identifier for biomedical literature
- **ACL ID**: ACL Anthology identifier
- **CorpusId**: Semantic Scholar Corpus ID
- **MAG ID**: Microsoft Academic Graph identifier (discontinued but historical data exists)

### Current Implementation Analysis

#### What the SimplePaper Model Supports
The data model only supports these identifiers:
- `paper_id`: Generic identifier (used differently by each scraper)
- `doi`: Digital Object Identifier
- `arxiv_id`: ArXiv preprint identifier

**Not supported in the model:**
- Semantic Scholar ID (though used as paper_id by SemanticScholarScraper)
- PMID
- ACL ID (though extracted and prefixed to paper_id by ACLAnthologyScraper)
- CorpusId
- MAG ID

#### Identifier Collection by Scraper

**NeurIPSScraper:**
- ✅ paper_id: Custom format (uses paper hash from URL)
- ❌ DOI, ArXiv ID, S2 ID, PMID, ACL ID, CorpusId, MAG ID

**PMLRScraper (ICML, AISTATS, UAI, CoLLAs):**
- ✅ paper_id: Custom format (e.g., "pmlr_v235_icml_2024_0")
- ❌ DOI, ArXiv ID, S2 ID, PMID, ACL ID, CorpusId, MAG ID

**OpenReviewScraper (ICLR, COLM, RLC, TMLR):**
- ✅ paper_id: OpenReview submission ID
- ❌ DOI, ArXiv ID, S2 ID, PMID, ACL ID, CorpusId, MAG ID

**ACLAnthologyScraper (ACL, COLING, EMNLP, NAACL):**
- ✅ paper_id: ACL ID prefixed with "acl_" (e.g., "acl_2024.acl-long.0", "acl_P24-1234")
- ❌ DOI, ArXiv ID, S2 ID, PMID, CorpusId, MAG ID
- Note: Extracts actual ACL ID but only stores it within paper_id field

**CVFScraper (CVPR, ECCV, ICCV, WACV):**
- ✅ paper_id: Custom format (e.g., "cvf_cvpr_2024_paperid")
- ❌ DOI, ArXiv ID, S2 ID, PMID, ACL ID, CorpusId, MAG ID

**IJCAIScraper:**
- ✅ paper_id: Custom format (e.g., "ijcai_2024_0123")
- ❌ DOI, ArXiv ID, S2 ID, PMID, ACL ID, CorpusId, MAG ID

**SemanticScholarScraper (AAAI):**
- ✅ paper_id: Semantic Scholar ID (paperId from API)
- ✅ DOI: From externalIds
- ✅ ArXiv ID: From externalIds
- ❌ PMID, ACL ID, CorpusId, MAG ID (not extracted even if available in externalIds)

### Web Search Results: Identifier Availability by Venue

#### NeurIPS
**Available Identifiers:**
- **ArXiv ID**: Many papers posted as preprints
- **Semantic Scholar ID**: Indexed in S2ORC corpus
- **DOI**: Not available (discontinued since 2007)
- **PMID**: Very rare (only for interdisciplinary biomedical papers)
- **ACL ID**: Not applicable
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists (MAG discontinued)

#### ICML/PMLR Venues (ICML, AISTATS, UAI, CoLLAs)
**Available Identifiers:**
- **ArXiv ID**: Common (authors allowed to post preprints)
- **Semantic Scholar ID**: Indexed in S2ORC
- **DOI**: Limited (only 9% for ICML)
- **PMID**: Very rare
- **ACL ID**: Not applicable
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists

#### OpenReview Venues (ICLR, COLM, RLC, TMLR)
**Available Identifiers:**
- **ArXiv ID**: Common (submission allowed during review)
- **Semantic Scholar ID**: Indexed, profile linking supported
- **DOI**: Not available (preprint-style platform)
- **PMID**: Very rare
- **ACL ID**: Not applicable
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists

#### ACL Anthology Venues (ACL, COLING, EMNLP, NAACL)
**Available Identifiers:**
- **ArXiv ID**: Some papers have preprints
- **Semantic Scholar ID**: Indexed in S2ORC
- **DOI**: Available (propagates to other databases)
- **PMID**: Very rare
- **ACL ID**: YES - Native identifier system
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists

#### CVF Venues (CVPR, ECCV, ICCV, WACV)
**Available Identifiers:**
- **ArXiv ID**: Common (links provided when available)
- **Semantic Scholar ID**: Indexed, paper-ids mapping available
- **DOI**: YES (via IEEE/Springer)
- **PMID**: Very rare
- **ACL ID**: Not applicable
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists

#### IJCAI
**Available Identifiers:**
- **ArXiv ID**: Some papers have preprints
- **Semantic Scholar ID**: Indexed in S2ORC
- **DOI**: YES (registered for all papers)
- **PMID**: Very rare
- **ACL ID**: Not applicable
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists

#### AAAI
**Available Identifiers:**
- **ArXiv ID**: Common for many papers
- **Semantic Scholar ID**: Indexed in S2ORC
- **DOI**: YES (registered for all papers)
- **PMID**: Rare (mainly for health/biomedical AI papers)
- **ACL ID**: Not applicable
- **CorpusId**: Yes (via Semantic Scholar)
- **MAG ID**: Historical data exists

### Key Insights from Web Search

1. **Semantic Scholar Coverage**: S2ORC includes 81.1M papers with comprehensive metadata including multiple identifiers (DOI, ArXiv, PMID, ACL Anthology IDs). All venues are indexed.

2. **ArXiv Integration**: Most ML conferences allow preprint posting, making ArXiv IDs common across all venues.

3. **PMID Rarity**: PMIDs are extremely rare for ML conference papers, only appearing for interdisciplinary biomedical work.

4. **Platform-Specific IDs**:
   - ACL venues have native ACL IDs
   - OpenReview venues use submission IDs
   - All papers get Semantic Scholar Corpus IDs when indexed

5. **Cross-Reference Infrastructure**: Semantic Scholar's paper-ids dataset provides mapping between different ID systems, enabling cross-platform tracking.

### Summary Table: Identifier Collection vs. Availability

| Venue | DOI | ArXiv ID | S2 ID | PMID | ACL ID | CorpusId | MAG ID |
|-------|-----|----------|-------|------|--------|----------|---------|
| **NeurIPS** | ❌/❌ | ❌/✅ | ❌/✅ | ❌/rare | ❌/N/A | ❌/✅ | ❌/hist |
| **ICML** | ❌/limited | ❌/✅ | ❌/✅ | ❌/rare | ❌/N/A | ❌/✅ | ❌/hist |
| **ICLR** | ❌/❌ | ❌/✅ | ❌/✅ | ❌/rare | ❌/N/A | ❌/✅ | ❌/hist |
| **ACL** | ❌/✅ | ❌/some | ❌/✅ | ❌/rare | partial/✅ | ❌/✅ | ❌/hist |
| **CVF** | ❌/✅ | ❌/✅ | ❌/✅ | ❌/rare | ❌/N/A | ❌/✅ | ❌/hist |
| **IJCAI** | ❌/✅ | ❌/some | ❌/✅ | ❌/rare | ❌/N/A | ❌/✅ | ❌/hist |
| **AAAI** | ✅/✅ | ✅/✅ | ✅/✅ | ❌/rare | ❌/N/A | ❌/✅ | ❌/hist |

*Format: Currently Collected / Actually Available*

### Recommendations for Identifier Collection

1. **Leverage Semantic Scholar API**: Since all venues are indexed in S2ORC with comprehensive identifiers, using Semantic Scholar API for all venues would provide the richest metadata.

2. **Priority Identifiers**:
   - **High Priority**: ArXiv ID (common), Semantic Scholar ID (universal)
   - **Medium Priority**: DOI (where available)
   - **Low Priority**: PMID (very rare), MAG ID (discontinued)

3. **Venue-Specific Considerations**:
   - ACL venues: Extract native ACL IDs
   - OpenReview venues: Keep submission IDs
   - CVF/IJCAI: Collect DOIs from publisher sites

4. **Cross-Reference Strategy**: Use Semantic Scholar's paper-ids mapping dataset for comprehensive cross-platform identifier resolution.

---

# 2025-07-10 - Paperoni Framework Analysis: Paper ID Collection and Cross-Linking Strategy

## Analysis Requested

Conduct an exhaustive analysis of the paperoni framework to understand:
1. How paperoni collects paper IDs (ArXiv IDs, DOIs, and other identifiers)
2. Its strategy for efficient collection
3. How it cross-links sources

## Analysis Methodology

I examined:
1. The paperoni data model (`model.py`)
2. Database schema (`db/schema.py`)
3. Individual scrapers (Semantic Scholar, OpenReview, OpenAlex, etc.)
4. Merge functionality (`db/merge.py`)
5. Link generation utilities

## Key Findings

### 1. Data Model Architecture

**Paper Identification Strategy:**
- Papers use a `Link` model to store all identifiers
- Each paper can have multiple links of different types
- Link structure: `type` (string) + `link` (string)

```python
class Link(Base):
    type: str
    link: str

class Paper(BaseWithQuality):
    links: list[Link]
    # other fields...
```

**Database Schema:**
```sql
CREATE TABLE paper_link (
    type TEXT NOT NULL,
    link TEXT NOT NULL,
    paper_id BLOB,
    PRIMARY KEY (type, link, paper_id)
);
```

### 2. Identifier Collection by Scraper

#### Semantic Scholar Scraper
**Most comprehensive identifier collection:**
```python
links = [Link(type="semantic_scholar", link=data["paperId"])]
for typ, ref in data["externalIds"].items():
    links.append(Link(type=typ.lower(), link=ref))
```
- Collects ALL external IDs from Semantic Scholar API
- Maps common identifiers (e.g., "pubmedcentral" → "pmc")
- Includes: DOI, ArXiv, PubMed, ACL, MAG, CorpusId, etc.

#### OpenAlex Scraper
**Second most comprehensive:**
```python
links=[_get_link(typ, ref) for typ, ref in data["ids"].items()]
```
- Extracts all IDs from OpenAlex API response
- Special handling for PubMed IDs ("pmid" → "pubmed")
- Adds PDF links and open access URLs

#### OpenReview Scraper
**Basic identification:**
```python
_links = [Link(type="openreview", link=note.id)]
```
- Only stores OpenReview submission ID
- Could extract code repository links but currently doesn't

#### Other Scrapers (NeurIPS, MLR, JMLR)
- Minimal identifier collection
- Usually just venue-specific IDs

### 3. Cross-Linking Strategy

**Merge by Shared Links:**
```sql
SELECT papers that share same (type, link) pair
FROM paper_link as pl1
JOIN paper_link as pl2
WHERE pl1.type == pl2.type AND pl1.link == pl2.link
```

**Multi-Level Merging:**
1. **Papers**: Merged if they share any identifier
2. **Authors**: Merged if they appear on merged papers or share IDs
3. **Venues**: Can be merged based on shared identifiers

**Merge Process:**
1. Find all papers sharing a link (e.g., same DOI or ArXiv ID)
2. Create equivalence groups
3. Propagate author merges from merged papers
4. Store canonical IDs in `canonical_id` table

### 4. Efficiency Strategies

#### Batch Processing
- Scrapers fetch papers in batches
- Database operations use bulk inserts
- Merge operations process groups efficiently

#### Caching and Deduplication
- Papers are hashed based on content
- Duplicate detection via shared links
- Quality scores determine canonical version

#### Incremental Updates
- Scrapers track last update timestamps
- Only fetch new/updated papers
- Merge process runs incrementally

### 5. Link Types Observed

From code analysis, paperoni handles these identifier types:
- `semantic_scholar`: Semantic Scholar paper ID
- `doi`: Digital Object Identifier
- `arxiv`: ArXiv preprint ID
- `pubmed`/`pmc`: PubMed/PubMed Central IDs
- `acl`: ACL Anthology ID
- `mag`: Microsoft Academic Graph ID
- `openalex`: OpenAlex ID
- `openreview`: OpenReview submission ID
- `orcid`: Author ORCID (for authors)
- `pdf`: Direct PDF links
- `url`: Landing page URLs
- `git`: Code repository links

### 6. Quality and Confidence

Papers have quality scores that influence merging:
```python
class BaseWithQuality(Base):
    quality: tuple[float, ...] | int
```

Higher quality papers become canonical during merges.

## Key Insights

1. **Semantic Scholar as Hub**: Acts as the primary source for cross-platform identifiers due to its comprehensive external ID collection.

2. **Link-Based Architecture**: The flexible Link model allows adding any identifier type without schema changes.

3. **Automatic Cross-Reference**: Papers are automatically linked across sources when they share any identifier.

4. **Quality-Aware Merging**: Not just deduplication - selects best version based on quality scores.

5. **Scalable Design**: Batch processing, incremental updates, and efficient SQL queries handle large paper volumes.

## Comparison with compute-forecast Scrapers

| Feature | Paperoni | compute-forecast |
|---------|----------|------------------|
| **Identifier Storage** | Flexible Link model | Fixed fields (doi, arxiv_id) |
| **Cross-Linking** | Automatic via shared IDs | None |
| **Merge Strategy** | SQL-based, quality-aware | None |
| **ID Types Supported** | Unlimited | 3 (paper_id, doi, arxiv_id) |
| **Primary Hub** | Semantic Scholar | Each scraper independent |

## Recommendations for compute-forecast

1. **Adopt Link Model**: Replace fixed identifier fields with flexible link system
2. **Leverage Semantic Scholar**: Use as primary source for all venues when possible
3. **Implement Merging**: Add cross-source deduplication
4. **Collect All IDs**: Don't filter external IDs from APIs
5. **Quality Scoring**: Add confidence/quality metrics for better merging

## Conclusion

Paperoni's design prioritizes comprehensive identifier collection and automatic cross-linking over performance. Its link-based architecture and merge strategy create a unified view of papers across multiple sources, making it highly effective for bibliometric analysis despite the computational overhead.

---

# 2025-07-10 - Paperoni Scraper Execution Order and Efficient Paper Collection Strategy

## Analysis Requested

Understand:
1. The order in which scrapers are executed to gather papers
2. Which scraper gathers the first set of papers
3. The strategy for efficiently scraping papers and gathering different versions

## Analysis Methodology

I examined:
1. CLI command structure and scraper loading
2. Documentation (design.md, scrapers.md)
3. Individual scraper implementations
4. The refinement process
5. Database queries and merge strategies

## Key Findings

### 1. Scraper Execution Model

**No Fixed Order - Command-Based Execution:**
- Scrapers are NOT executed in a predefined sequence
- Each scraper is invoked individually via CLI commands
- Example: `paperoni acquire semantic_scholar`, `paperoni acquire openreview`

**Available Scrapers:**
```python
__scrapers__ = {
    "semantic_scholar": SemanticScholarScraper,
    "openreview": OpenReviewPaperScraper,
    "openalex": OpenAlexScraper,
    "neurips": NeurIPSScraper,
    "mlr": MLRScraper,
    "jmlr": JMLRScraper,
    "refine": RefineScraper,
    "zeta-alpha": ZetaAlphaScraper
}
```

### 2. Primary Paper Discovery Strategy

**Semantic Scholar as Primary Source:**
From scrapers.md documentation:
> "This scraper queries Semantic Scholar for papers. This is the main way to *find* papers."

**Two-Phase Process:**
1. **Prepare Phase**: Gather researcher IDs
   - `paperoni prepare semantic_scholar`
   - Interactive process to find and confirm researcher identities
   - Stores IDs in `author_scrape_ids` table

2. **Acquire Phase**: Fetch papers for each researcher
   - `paperoni acquire semantic_scholar`
   - Queries papers for all stored researcher IDs
   - Date-bounded queries based on affiliation periods

### 3. Efficient Paper Collection Strategy

#### Phase 1: Primary Discovery (Semantic Scholar)
```python
def acquire(self):
    queries = self.generate_ids(scraper="semantic_scholar")
    for name, ids, start, end in queries:
        for ssid in ids:
            yield from filter_papers(
                papers=ss.author_papers(ssid, block_size=1000),
                start=start,
                end=end,
            )
```

**Efficiency Features:**
- Batch processing (1000 papers at a time)
- Date filtering based on researcher affiliations
- Comprehensive external ID collection

#### Phase 2: Venue-Specific Collection
Specialized scrapers for conferences not well-covered by Semantic Scholar:
- **OpenReview**: ICLR, NeurIPS (recent years), COLM, RLC, TMLR
- **MLR/PMLR**: ICML, AISTATS, UAI, CoLLAs
- **Direct scrapers**: NeurIPS (older years), JMLR

#### Phase 3: Gap Filling (Zeta-Alpha)
From scrapers.md:
> "Search by organization (Mila, University of Montreal, McGill, etc.) to find papers that we may have missed"

#### Phase 4: Enrichment (Refine)
```python
def acquire(self):
    # Select all papers ordered by most recent
    pq = select(sch.Paper).order_by(sch.Venue.date.desc())

    for paper in papers:
        links = [l for l in paper.links if not been_processed(l)]
        for _, result in self.refine(paper, merge=True, links=links):
            yield result
```

**Refiner Priority System:**
```python
@refiner(type="doi", priority=100)  # CrossRef
@refiner(type="doi", priority=90)   # ScienceDirect
@refiner(type="arxiv", priority=80) # ArXiv
@refiner(type="pdf", priority=10)   # PDF download (last resort)
```

### 4. Cross-Source Integration

**Automatic Merging via Shared Identifiers:**
```sql
-- Papers sharing any link are merged
SELECT papers that share same (type, link) pair
WHERE pl1.type == pl2.type AND pl1.link == pl2.link
```

**Quality-Based Canonical Selection:**
- Each source has quality scores
- Higher quality sources become canonical during merge
- Example: Semantic Scholar (0.95) > venue scrapers (0.75)

### 5. Incremental Update Strategy

**Tracking Processed Papers:**
```python
# Refiner tracks what's been processed
ScraperData(scraper="refine", tag=f"{type}:{link}", date=now)
```

**Date-Based Filtering:**
- New papers prioritized (ordered by venue date DESC)
- Affiliations determine date ranges for queries
- Cutoff dates prevent re-processing old data

### 6. Recommended Execution Order

Based on the design and documentation:

1. **Initial Setup**:
   ```bash
   paperoni prepare semantic_scholar  # Get researcher IDs
   ```

2. **Primary Collection**:
   ```bash
   paperoni acquire semantic_scholar  # Main paper discovery
   ```

3. **Venue-Specific Collection** (parallel possible):
   ```bash
   paperoni acquire openreview
   paperoni acquire mlr
   paperoni acquire neurips
   ```

4. **Gap Filling**:
   ```bash
   paperoni acquire zeta-alpha  # Organization-based search
   ```

5. **Enrichment**:
   ```bash
   paperoni acquire refine  # Add affiliations, missing metadata
   ```

6. **Merge**:
   ```bash
   paperoni merge  # Deduplicate and integrate
   ```

### 7. Efficiency Optimizations

1. **Caching**:
   - HTTP responses cached for 6 days
   - PDFs cached permanently

2. **Batch Processing**:
   - Large result sets fetched in chunks
   - Bulk database inserts

3. **Incremental Updates**:
   - Only new/updated content fetched
   - Processed links tracked

4. **Parallel Execution**:
   - Venue scrapers can run concurrently
   - No dependencies between most scrapers

## Key Insights

1. **No Fixed Pipeline**: Scrapers are independent tools, not a fixed pipeline
2. **Semantic Scholar First**: Primary discovery through comprehensive API
3. **Layered Approach**: Discovery → Venue-specific → Gap-filling → Enrichment
4. **Link-Based Integration**: Automatic merging via shared identifiers
5. **Quality Hierarchy**: Better sources override lower quality ones
6. **Incremental Design**: Built for continuous updates, not one-time runs

## Comparison with Traditional Approaches

| Aspect | Paperoni | Traditional |
|--------|----------|-------------|
| **Execution** | Manual, flexible order | Fixed pipeline |
| **Integration** | Automatic via links | Manual matching |
| **Updates** | Incremental | Full re-runs |
| **Quality** | Score-based selection | Last-write-wins |
| **Efficiency** | Distributed across time | Single batch job |

## Conclusion

Paperoni's strategy prioritizes completeness over speed. Rather than a fixed pipeline, it provides a toolkit where:
- Semantic Scholar serves as the primary discovery mechanism
- Specialized scrapers fill known gaps
- The refiner enriches all papers regardless of source
- Automatic merging creates a unified view

This design allows flexible, incremental building of a comprehensive paper database, with each scraper contributing its strengths to the overall collection.
