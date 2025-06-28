# State Management Directory

This directory contains the hierarchical state management system as specified in Issue #5.

## Directory Structure

```
data/states/
├── sessions/
│   ├── {session_id}/
│   │   ├── session_config.json      # Session configuration
│   │   ├── session_status.json      # Current session status
│   │   ├── checkpoints/
│   │   │   ├── checkpoint_001.json  # Individual checkpoints
│   │   │   ├── checkpoint_002.json
│   │   │   └── ...
│   │   ├── venues/
│   │   │   ├── {venue}_{year}_state.json  # Per-venue state
│   │   │   └── ...
│   │   └── recovery/
│   │       ├── interruption_analysis.json  # Interruption analysis
│   │       └── recovery_plan.json          # Recovery plan
│   └── ...
```

## File Formats

All files are JSON format with the following structures:

### session_config.json
Contains the initial session configuration including CollectionConfig parameters.

### session_status.json  
Contains the current session state as a CollectionSession object.

### checkpoints/*.json
Individual checkpoint files containing CheckpointData objects.

### venues/*.json
Per-venue state tracking for detailed recovery analysis.

### recovery/*.json
Interruption analysis and recovery plan data for session restoration.

## Usage

This directory is automatically managed by the StateManager class and should not be modified manually during active collection sessions.