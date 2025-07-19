# Consolidation Resumption Plan

**Date**: 2025-01-19  
**Title**: Design and Implementation Plan for Consolidation Checkpoint System

## Analysis Request
The user requested a plan to add resumption support to the consolidation command, with the following requirements:
- Track papers that were consolidated to avoid duplicate processing
- Support resumption at batch boundaries (not mid-batch)
- Use time-based checkpointing (every 5 minutes) instead of fixed batch counts

## Analysis Process

### 1. Current State Analysis
Examined the consolidation implementation to understand:
- **Single-stage process**: Sequential source processing (no multiple stages found)
- **Batch processing**: Papers processed in configurable batch sizes per source
- **Memory-based**: All results kept in memory until final save
- **No resumption**: Process must restart from beginning on failure

### 2. Existing Infrastructure Review
Found robust checkpoint system in metadata collection pipeline:
- **CheckpointManager**: Thread-safe checkpoint creation with integrity checks
- **StatePersistence**: Atomic file operations with SHA256 validation
- **Recovery planning**: Intelligent resumption with cause analysis
- Located in `.cf_state/` directory structure

### 3. Design Decisions

#### Checkpoint Structure
```json
{
    "session_id": "consolidate_20250119_123456",
    "input_file": "papers.json",
    "total_papers": 1500,
    "sources": {
        "semantic_scholar": {
            "status": "completed|in_progress|pending|failed",
            "batches_completed": 30,
            "total_batches": 30,
            "papers_processed": 1500,
            "enrichments": {
                "citations": 1200,
                "abstracts": 1100,
                "urls": 800,
                "identifiers": 1500
            }
        }
    },
    "last_checkpoint_time": "2025-01-19T10:15:30",
    "timestamp": "2025-01-19T10:15:30",
    "checksum": "sha256..."
}
```

#### Time-Based Checkpointing
- Checkpoint after each batch IF 5+ minutes elapsed since last checkpoint
- Always checkpoint after source completion
- Always checkpoint on errors before exit
- Configurable interval via `--checkpoint-interval` flag

#### Storage Layout
```
.cf_state/consolidate/
├── {session_id}/
│   ├── checkpoint.json         # Current state
│   ├── checkpoint.json.meta    # Checksum
│   └── papers_enriched.json    # Partial results
```

## Implementation Plan

### Phase 1: Core Infrastructure (2-3 hours)
1. Create `ConsolidationCheckpointManager` class
   - Extend existing checkpoint infrastructure
   - Implement time-based checkpoint logic
   - Handle atomic updates to papers_enriched.json

2. Add checkpoint hooks to consolidate.py
   - Initialize checkpoint manager
   - Add checkpoint calls after batches/sources
   - Handle checkpoint on errors

### Phase 2: State Persistence (2-3 hours)
1. Modify consolidate command interface
   - Add `--resume` flag
   - Add `--checkpoint-interval` option (default 5 minutes)
   - Generate unique session IDs

2. Implement incremental paper saving
   - Save enriched papers after each checkpoint
   - Merge new enrichments with existing data
   - Handle deduplication

### Phase 3: Resume Logic (2-3 hours)
1. Add resume detection and loading
   - Check for existing checkpoints
   - Load saved state and papers
   - Determine resume point

2. Modify processing loop for resumption
   - Skip completed sources
   - Resume from last completed batch
   - Update progress tracking

### Phase 4: Testing & Edge Cases (1-2 hours)
1. Test various scenarios
2. Handle edge cases (corruption, file changes)

## Outcomes
- Designed comprehensive checkpoint system adapted from existing infrastructure
- Time-based approach provides predictable checkpoint frequency
- Batch-level granularity balances overhead vs potential work loss
- Total implementation estimate: 8-11 hours