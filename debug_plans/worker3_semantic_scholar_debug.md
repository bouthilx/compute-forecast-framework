# Worker 3 Debug Plan - Semantic Scholar Filtering Issues

## Issue Summary
- **Status**: Medium Priority - API working but filtering failing
- **Root Cause**: Search filtering logic not correctly identifying valid papers
- **Error Pattern**: Finding 23,961 papers but 0 meet filtering criteria for NeurIPS 2024
- **Impact**: No papers collected despite API returning results
- **Last Update**: 2025-06-26 19:55:52

## Debug Session Plan

### Phase 1: Search Query Analysis
1. **Venue Matching Investigation**
   - Debug how "NeurIPS" is matched against actual venue names in results
   - Test different venue name formats ("NeurIPS", "NIPS", "Neural Information Processing Systems")
   - Examine raw API response venue fields for NeurIPS papers

2. **Query Parameter Testing**
   - Test different query formats: 'venue:"NeurIPS"' vs venue matching in results
   - Validate year filtering: 'year:2024' parameter effectiveness
   - Test field selection impact on results

3. **API Response Validation**
   - Log 5-10 raw API responses for manual inspection
   - Compare expected vs actual venue names in results
   - Verify paper metadata completeness

### Phase 2: Result Filtering Debug
1. **Citation Threshold Analysis**
   - Check if citation count requirements are too restrictive
   - Test with different min_citations values (0, 1, 5, 10)
   - Verify citation count parsing from API responses

2. **Paper Validation Logic**
   - Debug paper parsing in `_parse_semantic_result()` method
   - Check for exceptions during paper object creation
   - Validate all required fields are present and correctly formatted

3. **Domain Classification**
   - Verify domain assignment logic
   - Check if papers are being rejected due to domain mismatch
   - Test with known NeurIPS 2024 papers

### Phase 3: Systematic Testing
1. **Known Paper Validation**
   - Test with specific NeurIPS 2024 paper IDs/titles
   - Verify these papers can be found and parsed correctly
   - Compare API response with expected paper data

2. **Search Parameter Optimization**
   - Test different combinations of search parameters
   - Optimize field selection for better venue matching
   - Experiment with query string formatting

3. **Logging Enhancement**
   - Add detailed logging for filtering decisions
   - Log reasons why papers are rejected
   - Track success/failure rates for different query types

## Debug Tools Needed
- API response logging
- Paper validation debugging
- Query parameter testing framework
- Known paper database for validation

## Success Criteria
- [ ] Successfully collect NeurIPS 2024 papers from Semantic Scholar
- [ ] Achieve >50% success rate for venue-specific searches
- [ ] Correctly parse and validate paper metadata
- [ ] Document optimal search parameters and filtering logic

## Testing Plan
1. Test with NeurIPS 2024 search (current failing case)
2. Test with other major venues (ICML, ICLR) for comparison
3. Validate against known paper lists
4. Test edge cases and error handling

## Priority: MEDIUM - API functional but results filtered incorrectly
