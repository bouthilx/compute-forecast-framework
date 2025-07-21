# 2025-01-19 Phase 1 Progress Bar Enhancement

## Request
The user requested that the Phase 1 progress bar show the percentage of papers with each type of ID found:
```
Harvesting identifiers -------- % (n/total) duration (eta) [DOI:% ArXiv:% OA:% SC: % CR %]
```

## Implementation

### 1. Created Phase1ProgressColumn Class
A new custom progress column class specifically for Phase 1 that:
- Shows standard progress information (percentage, count, elapsed time, ETA)
- Calculates and displays percentages for each ID type:
  - DOI: % of papers with DOI
  - ArXiv: % of papers with ArXiv ID
  - OA: % of papers with OpenAlex ID
  - S2: % of papers with Semantic Scholar ID
  - PM: % of papers with PubMed ID (instead of CR)

### 2. Modified Phase 1 Progress Display
- Created a separate Progress instance for Phase 1 with the custom column
- Passed the identifiers dictionary reference to the column for real-time updates
- Used `live.update()` to switch between progress displays
- Restored the main progress display after Phase 1 completes

### 3. Progress Format
The final format shows:
```
5.2% (52/1000) 00:02:45 (2025-01-19 15:32:10) [DOI: 85% ArXiv: 12% OA:100% S2:  0% PM:  3%]
```

## Benefits
1. **Real-time Visibility**: Users can see which types of IDs are being found during processing
2. **Quality Metrics**: Immediate feedback on ID coverage helps identify data quality issues
3. **Performance Monitoring**: Shows if certain ID types are missing or underrepresented
4. **Debugging Aid**: Helps diagnose issues with ID extraction

## Technical Details
- The Phase1ProgressColumn maintains a reference to the identifiers dictionary
- On each render, it calculates percentages based on completed tasks
- The column updates in real-time as identifiers are discovered
- Uses Rich's Live display to smoothly switch between progress instances

## Summary
The enhanced progress bar provides detailed visibility into the ID harvesting process, showing not just completion progress but also the quality and distribution of discovered identifiers.
