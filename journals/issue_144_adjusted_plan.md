# Issue #144 Adjusted Implementation Plan

**Timestamp**: 2025-07-07
**Title**: IJCAI Conference Scraper - Adjusted Plan with Fixes

## Revised Implementation Plan

### Phase 1: Fix Codebase Discrepancies (1-1.5 hours)

#### 1.1 Fix Class Name Typos
- **File**: `compute_forecast/data/sources/scrapers/base.py`
- **Changes**:
  - Rename `BaseScaper` to `BaseScraper`
  - Rename `ConferenceProceedingsScaper` to `ConferenceProceedingsScraper`
  - Update docstrings and comments

#### 1.2 Create Missing Models
- **File**: `compute_forecast/data/sources/scrapers/models.py`
- **Add**:
  ```python
  @dataclass
  class ScrapedAuthor:
      name: str
      position: int
      affiliation: Optional[str] = None
      orcid: Optional[str] = None

  @dataclass
  class ScrapedPaper:
      paper_id: str
      title: str
      authors: List[ScrapedAuthor]
      venue: str
      year: int
      pdf_urls: List[str]
      source_scraper: str
      source_url: str
      metadata_completeness: float
      extraction_confidence: float
      abstract: Optional[str] = None
      doi: Optional[str] = None
      arxiv_id: Optional[str] = None
      citation_count: Optional[int] = None
  ```

#### 1.3 Update Base Classes
- Modify `ConferenceProceedingsScraper` to return `ScrapedPaper` objects
- Update method signatures to use new models
- Ensure backward compatibility or update existing scrapers

#### 1.4 Update Imports
- Find and update all files importing the renamed classes
- Update any existing scrapers using `SimplePaper`

### Phase 2: Implement IJCAI Scraper (2-3 hours)

#### 2.1 Create IJCAI Scraper File
- **File**: `compute_forecast/data/sources/scrapers/conference_scrapers/ijcai_scraper.py`
- Implement `IJCAIScraper` class inheriting from fixed `ConferenceProceedingsScraper`
- Use proper imports with corrected class names

#### 2.2 Core Functionality
- Implement URL construction for IJCAI proceedings
- Add year discovery (2018-2024)
- Handle base URL: `https://www.ijcai.org/proceedings/{year}/`

#### 2.3 Parsing Implementation
- Parse HTML to extract paper information
- Extract:
  - Paper titles
  - Author lists with positions
  - PDF URLs
  - Paper IDs from filenames
- Calculate metadata completeness scores

### Phase 3: Testing & Validation (1-1.5 hours)

#### 3.1 Unit Tests
- Test URL generation
- Test HTML parsing with sample data
- Test error handling

#### 3.2 Integration Tests
- Test with live IJCAI proceedings
- Validate 1,000+ papers extraction
- Test rate limiting behavior

#### 3.3 Data Validation
- Spot-check extracted papers
- Verify PDF URLs are valid
- Check author extraction accuracy

### Phase 4: Integration & Documentation (0.5-1 hour)

#### 4.1 Integration
- Add IJCAI scraper to scraper registry
- Ensure compatibility with collection pipeline
- Test with existing infrastructure

#### 4.2 Documentation
- Update scraper documentation
- Document the model changes
- Add usage examples

## Estimated Timeline

1. **Fix Discrepancies**: 1-1.5 hours
2. **Implement Scraper**: 2-3 hours
3. **Testing**: 1-1.5 hours
4. **Integration**: 0.5-1 hour

**Total**: 4.5-7 hours (within M estimate)

## Benefits of Fixing Discrepancies

1. **Consistency**: Matches issue specifications exactly
2. **Clarity**: Fixes confusing typos in class names
3. **Extensibility**: Proper author modeling for future enhancements
4. **Maintainability**: Clear separation between scraped and processed data

## Risk Mitigation

- **Backward Compatibility**: Check for existing code using old names
- **Testing**: Thoroughly test changes don't break existing scrapers
- **Incremental**: Fix typos first, then add models, then implement
- **Validation**: Ensure all tests pass after each phase

## Success Criteria

- [ ] All class name typos fixed
- [ ] ScrapedPaper and ScrapedAuthor models created
- [ ] Existing code updated to use new names/models
- [ ] IJCAI scraper successfully extracts 1,000+ papers
- [ ] All tests passing
- [ ] Integration with pipeline verified
