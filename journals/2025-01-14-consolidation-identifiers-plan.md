# Plan: Adding Paper Identifiers During Consolidation

**Date**: 2025-01-14
**Task**: Design and plan implementation for adding DOI, ArXiv ID, S2 ID, PMID, ACL ID, CorpusId, and MAG ID during consolidation

## Executive Summary

This plan outlines how to extend the consolidation process to capture and store additional paper identifiers from enrichment sources. The implementation preserves the existing provenance tracking pattern while adding new identifier types.

## Current State Analysis

### Existing Paper Model Fields
- `paper_id`: Semantic Scholar ID (optional)
- `openalex_id`: OpenAlex ID (optional)
- `arxiv_id`: ArXiv ID (optional)
- `doi`: DOI (string field)

### Missing Identifiers
- **S2 CorpusId**: Semantic Scholar's internal corpus identifier
- **PMID**: PubMed ID for biomedical papers
- **ACL ID**: ACL Anthology identifier
- **MAG ID**: Microsoft Academic Graph ID (legacy but useful)

### Current Consolidation Behavior
- Uses existing identifiers to **find** papers in sources
- Extracts only citations, abstracts, and URLs
- Does NOT update or add new identifiers discovered during enrichment

## Proposed Solution

### 1. Data Model Extensions

#### Option A: Add Individual Fields (Simple)
```python
# In Paper model (models.py)
@dataclass
class Paper:
    # Existing fields...
    
    # Extended identifier fields
    s2_corpus_id: Optional[str] = None  # Semantic Scholar Corpus ID
    pmid: Optional[str] = None          # PubMed ID
    acl_id: Optional[str] = None        # ACL Anthology ID
    mag_id: Optional[str] = None        # Microsoft Academic Graph ID
```

#### Option B: Identifier Records with Provenance (Recommended)
```python
# In consolidation/models.py
@dataclass
class IdentifierData:
    """Paper identifier data"""
    identifier_type: str  # 'doi', 'arxiv', 's2_paper', 's2_corpus', 'pmid', 'acl', 'mag', 'openalex'
    identifier_value: str

@dataclass
class IdentifierRecord(ProvenanceRecord):
    """Identifier with provenance tracking"""
    data: IdentifierData

# In EnrichmentResult
@dataclass
class EnrichmentResult:
    paper_id: str
    citations: List[CitationRecord] = field(default_factory=list)
    abstracts: List[AbstractRecord] = field(default_factory=list)
    urls: List[URLRecord] = field(default_factory=list)
    identifiers: List[IdentifierRecord] = field(default_factory=list)  # NEW
    errors: List[Dict[str, str]] = field(default_factory=list)
```

### 2. Source Implementation Changes

#### Semantic Scholar Source Modifications
```python
def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    # Existing fields + request corpusId
    fields = "paperId,title,abstract,citationCount,year,authors,externalIds,corpusId,openAccessPdf,fieldsOfStudy,venue"
    
    # In response parsing:
    paper_data = {
        'citations': item.get('citationCount'),
        'abstract': item.get('abstract'),
        'urls': [],
        'identifiers': [],  # NEW
        # ... other fields
    }
    
    # Extract all external IDs
    ext_ids = item.get('externalIds', {})
    
    # Add Semantic Scholar IDs
    if item.get('paperId'):
        paper_data['identifiers'].append({
            'type': 's2_paper',
            'value': item['paperId']
        })
    
    if item.get('corpusId'):
        paper_data['identifiers'].append({
            'type': 's2_corpus',
            'value': str(item['corpusId'])
        })
    
    # Add external identifiers
    id_mappings = {
        'DOI': 'doi',
        'ArXiv': 'arxiv',
        'PubMed': 'pmid',
        'ACL': 'acl',
        'MAG': 'mag'
    }
    
    for ext_type, our_type in id_mappings.items():
        if ext_type in ext_ids:
            paper_data['identifiers'].append({
                'type': our_type,
                'value': ext_ids[ext_type]
            })
```

#### OpenAlex Source Modifications
```python
def fetch_all_fields(self, source_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    # Request additional ID fields
    select_fields = "id,title,abstract_inverted_index,cited_by_count,ids,publication_year,..."
    
    # In response parsing:
    paper_data = {
        # ... existing fields
        'identifiers': []  # NEW
    }
    
    # Extract all IDs from OpenAlex
    ids = work.get('ids', {})
    
    # OpenAlex ID (already in URL format)
    if work.get('id'):
        paper_data['identifiers'].append({
            'type': 'openalex',
            'value': work['id']
        })
    
    # Other identifiers
    id_mappings = {
        'doi': 'doi',
        'pmid': 'pmid',
        'mag': 'mag'  # OpenAlex has MAG IDs
    }
    
    for oa_type, our_type in id_mappings.items():
        if oa_type in ids:
            paper_data['identifiers'].append({
                'type': our_type,
                'value': ids[oa_type]
            })
```

### 3. Consolidation Command Updates

```python
# In consolidate.py main()
def update_progress(result):
    # ... existing code ...
    
    # Add identifier enrichments
    paper.identifiers.extend(result.identifiers)  # NEW
    
    # Track statistics
    source_identifiers += len(result.identifiers)  # NEW

# Update statistics tracking
stats = {
    "total_papers": len(papers),
    "citations_added": 0,
    "abstracts_added": 0,
    "urls_added": 0,
    "identifiers_added": 0,  # NEW
    "api_calls": {}
}
```

### 4. Paper Model Integration

If using Option B (recommended), we need to update the Paper model to handle identifier records:

```python
# In Paper class
def update_identifiers_from_records(self):
    """Update individual identifier fields from identifier records"""
    for record in self.identifiers:
        id_type = record.data.identifier_type
        id_value = record.data.identifier_value
        
        if id_type == 'doi' and not self.doi:
            self.doi = id_value
        elif id_type == 'arxiv' and not self.arxiv_id:
            self.arxiv_id = id_value
        elif id_type == 'openalex' and not self.openalex_id:
            self.openalex_id = id_value
        elif id_type == 's2_paper' and not self.paper_id:
            self.paper_id = id_value
        # Store new identifier types in processing_flags or a new field
        else:
            if 'discovered_identifiers' not in self.processing_flags:
                self.processing_flags['discovered_identifiers'] = {}
            self.processing_flags['discovered_identifiers'][id_type] = id_value
```

## Implementation Priority

### Phase 1: Core Identifiers (2-3 hours)
1. Add IdentifierRecord to consolidation models
2. Update EnrichmentResult to include identifiers
3. Modify base consolidation source class

### Phase 2: Semantic Scholar Integration (2-3 hours)
1. Update S2 source to extract all externalIds
2. Add corpusId extraction
3. Test with real API responses

### Phase 3: OpenAlex Integration (2-3 hours)
1. Update OpenAlex source to extract IDs
2. Map OpenAlex ID types to our schema
3. Test with real API responses

### Phase 4: Paper Model Updates (1-2 hours)
1. Add new identifier fields or storage mechanism
2. Update serialization/deserialization
3. Ensure backward compatibility

### Phase 5: Testing & Documentation (2-3 hours)
1. Add unit tests for identifier extraction
2. Update integration tests
3. Document new fields and behavior

## Benefits

1. **Complete Paper Identity**: Papers will have all available identifiers for cross-referencing
2. **Better Deduplication**: More identifiers mean better matching across sources
3. **Enhanced Interoperability**: Easier integration with other academic databases
4. **Provenance Tracking**: Know which source provided which identifier

## Considerations

1. **Storage Impact**: Minimal - just additional string fields
2. **API Response Size**: Negligible increase in API response parsing
3. **Backward Compatibility**: Existing code continues to work with new optional fields
4. **Performance**: No significant impact on consolidation speed

## Alternative Approaches Considered

1. **Separate Identifier Collection Pass**: Run a dedicated pass just for identifiers
   - Pros: Clean separation of concerns
   - Cons: Additional API calls, slower overall process

2. **Post-Processing Enhancement**: Add identifiers after main consolidation
   - Pros: Doesn't change existing flow
   - Cons: Requires re-parsing already fetched data

3. **External Identifier Service**: Build separate service for ID resolution
   - Pros: Reusable, specialized
   - Cons: Over-engineering for current needs

## Recommendation

Implement **Option B** (Identifier Records with Provenance) as it:
- Maintains consistency with existing provenance tracking
- Provides flexibility for new identifier types
- Preserves source attribution for each identifier
- Enables future expansion without model changes