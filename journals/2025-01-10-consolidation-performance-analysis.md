# Consolidation Performance Analysis and Rate Limits

**Date**: 2025-01-10
**Author**: Assistant

## Performance Analysis Summary

### Current Performance Issues
- Processing 450 papers takes 17-20 minutes
- Primary bottleneck: 1 request/second rate limiting (80% of time)
- Secondary issue: Small batch sizes (10 papers) creating excessive API calls

### API Rate Limits

#### Semantic Scholar
- **Default (no API key - CURRENT STATUS)**: Shared pool of 5,000 requests/5 minutes among ALL users
  - Using conservative 0.1 requests/second (1 per 10 seconds) to avoid 429 errors
- **With API key (pending approval)**: 1 request/second (dedicated)
- **Enhanced tier**: 10 requests/second (after demonstrating good usage)
- **Maximum batch size**: 500 papers per request

**Application Status**: Submitted API key request on 2025-01-10 with:
- Project description emphasizing open-access research report
- Expected usage: 300-500 requests/day for 60,000+ papers
- Endpoints: /graph/v1/paper/batch and /graph/v1/paper/search
- **Currently waiting for approval**

#### OpenAlex
- **Default**: 100,000 calls/day, 10 requests/second
- **Polite pool**: Same limits but prioritized (using email in User-Agent)
- **Premium (free for academics)**: Higher limits available on request
- **Maximum practical batch size**: 50 papers (URL length limits)

**Recommendation**: Current limits are sufficient. No need to request premium access yet.

### Performance Bottlenecks Breakdown

1. **Rate Limiting Impact**: 315 API calls × 1 second = 5.25 minutes minimum
2. **Excessive API Calls**:
   - Current: 45 batches × 7 calls/batch = 315 total calls
   - Optimal: ~12 calls total (using max batch sizes)
3. **Sequential Processing**: Sources processed one after another

### Optimization Plan

1. **Increase batch sizes**:
   - Semantic Scholar: 10 → 500 papers/batch
   - OpenAlex: 10 → 50 papers/batch

2. **Source-specific configurations**:
   - Add per-source batch size settings
   - Respect API-specific limits

3. **Progress tracking alternatives**:
   - Update progress during batch parsing if feasible
   - Accept less frequent updates for better performance

### Expected Improvements

- **Before optimization**: 17-20 minutes for 450 papers (with 10 paper batches)
- **Current (no API key)**: ~3-4 minutes for 450 papers
  - 20 API calls × 10 seconds = 200 seconds for Semantic Scholar
  - 10 API calls × 0.1 seconds = 1 second for OpenAlex
  - Plus processing overhead
- **Future (with API key)**: ~20-30 seconds for 450 papers
  - 20 total API calls × 1 second average
- API calls reduced from 315 to ~20

### Next Steps

1. Implement source-specific batch configurations
2. Remove artificial batch size reduction for progress
3. Consider parallel source processing in future
4. Monitor Semantic Scholar API key approval
