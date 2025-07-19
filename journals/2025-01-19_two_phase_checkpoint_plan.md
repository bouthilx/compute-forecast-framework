# Two-Phase Consolidation Checkpoint Plan

**Date**: 2025-01-19  
**Title**: Checkpoint System for Two-Phase Consolidation Implementation

## Overview
Add checkpoint support to the new two-phase consolidation implementation to enable resumption after failures or interruptions. The system needs to handle the multi-phase nature and batch processing within each phase.

## Current Implementation Analysis

### Three-Phase Structure
1. **Phase 1**: OpenAlex ID Harvesting
   - Batch title searches (50 papers/batch) 
   - Batch ID lookups for discovered OpenAlex IDs
   - Returns Dict[paper_id, PaperIdentifiers]

2. **Phase 2**: Semantic Scholar Batch Enrichment
   - Uses discovered external IDs for efficient batch lookups
   - Processes up to 500 papers per API call
   - Updates Paper objects with enrichments

3. **Phase 3**: OpenAlex Full Enrichment
   - Uses standard enrich_papers method
   - Processes all papers with discovered OpenAlex IDs

### Key Differences from Original
- Phase state tracking needed (ConsolidationPhaseState already exists)
- Identifier collection is a separate data structure
- Papers are modified in-place rather than creating EnrichmentResults

## Checkpoint Design

### State Structure
```json
{
    "session_id": "consolidate_20250119_123456_abc123",
    "input_file": "papers.json", 
    "total_papers": 500,
    "phase_state": {
        "phase": "id_harvesting|semantic_scholar_enrichment|openalex_enrichment|completed",
        "phase_completed": false,
        "phase_start_time": "2025-01-19T10:00:00",
        "phase_end_time": null,
        "identifiers_collected": {...},  // Dict[paper_id, PaperIdentifiers]
        "papers_with_dois": 150,
        "papers_with_arxiv": 200,
        "papers_with_external_ids": 350,
        "batch_progress": {
            "current_batch_start": 250,  // For resume within phase
            "batches_completed": 5
        }
    },
    "sources": {
        "phase1_openalex": {"status": "completed", "api_calls": 50},
        "phase2_semantic_scholar": {"status": "in_progress", "api_calls": 2},
        "phase3_openalex": {"status": "pending", "api_calls": 0}
    },
    "last_checkpoint_time": "2025-01-19T10:15:00",
    "timestamp": "2025-01-19T10:15:00"
}
```

### Checkpoint Triggers
1. **Phase boundaries**: Always checkpoint when completing a phase
2. **Time-based**: Within phases, checkpoint after batch if 5+ minutes elapsed

## Implementation Plan

### Step 1: Extend Checkpoint Manager (1-2 hours)
- The existing ConsolidationCheckpointManager already has phase_state field
- Add methods to save/load phase-specific state:
  - `save_phase_state()` - serialize ConsolidationPhaseState
  - `load_phase_state()` - deserialize and restore state
- Ensure identifier mappings are properly serialized

### Step 2: Add Checkpoint Hooks to Each Phase (2-3 hours)

#### Phase 1 Checkpointing
- Checkpoint after each batch in `harvest_identifiers_openalex()`
- Save partial identifier mappings
- Track batch progress for mid-phase resume

#### Phase 2 Checkpointing  
- Checkpoint after each 500-paper batch in `enrich_semantic_scholar_batch()`
- Papers already modified in-place, so just save current state
- Track which paper IDs have been processed

#### Phase 3 Checkpointing
- Use existing checkpoint support in OpenAlex enrich_papers
- Just needs phase state updates

### Step 3: Implement Resume Logic (2-3 hours)

#### Main Function Changes
- Load checkpoint if --resume flag set
- Restore phase state and identifiers_collected
- Skip to appropriate phase based on checkpoint
- Within phase, skip already-processed batches

#### Phase-Specific Resume
- Phase 1: Skip papers already in identifiers_collected
- Phase 2: Skip papers already enriched (check for S2 data presence)
- Phase 3: Let OpenAlex source handle its own resume logic

### Step 4: Testing Scenarios (1 hour)
- Interrupt at each phase boundary
- Interrupt mid-batch in each phase
- Resume with modified input file (should detect and warn)
- Checkpoint file corruption handling

## Key Simplifications
1. **No source selection**: Hardcoded three-phase flow simplifies state
2. **In-place updates**: Papers modified directly, no merge complexity
3. **Existing infrastructure**: Reuse ConsolidationCheckpointManager
4. **Phase isolation**: Each phase has clear inputs/outputs

## Time Estimate
- Total: 6-9 hours
- Lower than original estimate due to:
  - Existing phase_state support in checkpoint manager
  - Simpler data flow (no EnrichmentResult merging)
  - Fixed phase sequence (no dynamic source selection)

## Next Steps
1. Start with Step 1 - minimal checkpoint manager updates
2. Add checkpointing to Phase 1 first (most time-consuming phase)
3. Test Phase 1 resume before proceeding to other phases
4. Implement remaining phases incrementally