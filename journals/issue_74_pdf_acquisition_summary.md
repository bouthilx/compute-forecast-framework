# PDF Acquisition Summary and Recommendations

**Timestamp**: 2025-07-01 18:30
**Title**: Results and Next Steps for PDF Infrastructure

## Current Status

### Test Results
From our limited testing:
- **Initial S2 test**: 40% PDF availability
- **Real acquisition test**: 50% success rate (5/10 papers)
- **Sources working**:
  - Semantic Scholar openAccessPdf: ~20-30%
  - ArXiv search: ~20% (when working)
  - Cache: Prevents re-downloads

### Issues Encountered
1. **ArXiv parsing error**: "string indices must be integers" - needs debugging
2. **403 errors**: Some PDFs blocked download (likely need better headers)
3. **Empty paper IDs**: Some papers generating ".pdf" filenames
4. **Rate limiting**: Process is slow (~2-3s per paper minimum)

### Coverage Analysis
Based on our tests, with current implementation:
- **Semantic Scholar PDFs**: ~30% coverage
- **ArXiv PDFs**: ~20% coverage (when fixed)
- **Combined**: ~40-50% coverage

This is still far from the 95%+ requirement.

## Gap Analysis

### Missing Sources Not Yet Implemented
1. **Google Scholar** - Could add 20-30%
2. **Unpaywall** (needs DOIs) - Could add 10-15%
3. **Conference sites** - Could add 10-20%
4. **Institutional repositories** - Could add 5-10%
5. **ResearchGate/Academia.edu** - Could add 10%

### Technical Gaps
1. **No web scraping** - Just using APIs
2. **No conference-specific parsers** - Would help for NeurIPS, ICML, etc.
3. **No author website search** - Many authors host PDFs
4. **No citation mining** - Could find via references

## Recommendations

### Option 1: Full Implementation (2-3 days)
Complete all PDF sources to achieve 95%+ coverage:

```python
# Priority order
1. Fix ArXiv parser bug
2. Implement Google Scholar scraping
3. Add conference-specific downloaders
4. Implement web search fallback
5. Add manual review queue for remaining
```

**Pros**: Achieves required coverage
**Cons**: Significant time investment

### Option 2: Hybrid Approach (1 day)
1. Fix current bugs (ArXiv parser, 403 errors)
2. Run on all 362 benchmark papers
3. Manually find PDFs for top 50-100 papers
4. Accept 60-70% automated coverage

**Pros**: Faster, still viable for analysis
**Cons**: Manual work required

### Option 3: Alternative Data Strategy (4-6 hours)
1. Use Semantic Scholar API v2 for better abstracts
2. Focus on papers with existing good abstracts
3. Enhance extraction to work with limited text
4. Lower expectations for affiliation coverage

**Pros**: Avoids PDF complexity
**Cons**: Lower quality results

## Critical Decision Point

The current 40-50% PDF coverage is insufficient. We need to either:

1. **Invest in full PDF infrastructure** (2-3 days) to achieve 95%+ coverage
2. **Accept hybrid automation + manual** (1 day) for 70-80% coverage
3. **Pivot to non-PDF strategy** and work with available metadata

### My Recommendation

Given the project timeline and blocking of M3-2, I recommend **Option 2 (Hybrid)**:

1. **Today**: Fix bugs, run on all benchmark papers
2. **Tomorrow**: Manually acquire PDFs for high-impact papers
3. **Result**: 70-80% coverage, sufficient for meaningful analysis

This balances time investment with quality needs.

## Next Steps

If proceeding with Option 2:

1. **Fix ArXiv parser** (30 min)
2. **Fix 403 errors with better headers** (30 min)
3. **Run on all 362 benchmark papers** (2-3 hours)
4. **Analyze coverage gaps** (30 min)
5. **Manual PDF acquisition for top papers** (2-3 hours)

Total: ~6-7 hours for 70-80% coverage

## Alternative: Enhanced Metadata Approach

If PDF acquisition proves too complex:

1. **Use S2 Graph API** for citation networks
2. **Use S2 Recommendations API** for related papers
3. **Extract more from titles** using NLP
4. **Lower affiliation requirements** to 50%

This would unblock M3-2 faster but with lower quality.
