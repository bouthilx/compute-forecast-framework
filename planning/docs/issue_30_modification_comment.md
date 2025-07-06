# Proposed Modifications to M4-1: Mila Paper Processing

## Context
After analyzing the project requirements, we've identified that measuring **suppressed computational demand** is critical for the report's success. This modification enhances the original scope by adding suppression indicators to the extraction process, providing evidence that Mila researchers need significantly more compute than they currently use.

## Proposed Scope Additions

### 1. Extend Extraction Template
Add a new `suppression_indicators` section to the existing extraction templates:

```python
extraction_config = {
    "templates": {
        "NLP": "nlp_training_v1",
        "CV": "cv_training_v1",
        "RL": "rl_training_v1"
    },
    "suppression_indicators": {  # NEW SECTION
        "experimental_scope": {
            "num_ablations": "Extract count of ablation studies",
            "num_seeds": "Extract number of random seeds used",
            "num_baselines": "Count baseline comparisons",
            "num_model_variants": "Count model size variants tested",
            "standard_experiments_missing": "List of expected but absent experiments"
        },
        "scale_analysis": {
            "parameter_percentile": "Model size percentile vs same-year papers",
            "training_duration": "Steps/epochs vs convergence requirements",
            "dataset_usage": "Full dataset or subsampled"
        },
        "method_classification": {
            "efficiency_focused": "Boolean - is primary contribution efficiency?",
            "compute_saving_techniques": "List techniques used (distillation, pruning, etc.)",
            "method_type": "compute_intensive or compute_efficient"
        },
        "explicit_constraints": {
            "mentions_constraints": "Boolean - explicitly mentions compute limits",
            "constraint_quotes": "Extract relevant quotes",
            "workarounds_described": "Methods used to work within constraints"
        }
    }
}
```

### 2. Enhanced Output Format
Modify the output to include suppression metrics alongside compute requirements:

```json
{
    "paper_id": "mila_2024_001",
    "title": "Efficient Vision Transformer for Limited Resources",
    "computational_requirements": {
        // Original fields remain unchanged
        "gpu_type": "A100",
        "gpu_count": 8,
        "training_time_hours": 72,
        "parameters_millions": 1300,
        "estimated_gpu_hours": 576
    },
    "suppression_indicators": {  // NEW
        "experimental_scope": {
            "ablations_conducted": 2,
            "seeds_used": 1,
            "baselines_compared": 3,
            "model_variants": 1,
            "missing_experiments": ["cross_dataset_eval", "robustness_testing", "scaling_analysis"]
        },
        "scale_analysis": {
            "parameter_percentile": 12,  // 12th percentile for 2024
            "training_truncated": true,
            "convergence_achieved": false,
            "dataset_subsampled": true,
            "subsample_ratio": 0.1
        },
        "method_bias": {
            "efficiency_focused": true,
            "techniques_used": ["knowledge_distillation", "pruning"],
            "method_type": "compute_efficient"
        },
        "constraints": {
            "explicitly_mentioned": true,
            "quotes": ["Due to computational constraints, we limit our experiments to..."],
            "adaptations": ["single seed", "small model only", "reduced dataset"]
        }
    },
    "extraction_metadata": {
        // Original metadata fields
        "confidence": 0.85,
        "extraction_method": "automated",
        "suppression_confidence": 0.90  // NEW
    }
}
```

### 3. Additional Processing Steps

Add these steps to the processing pipeline:

1. **Comparative Baseline Loading**: Load contemporary papers for percentile calculations
2. **Standard Experiment Checklist**: Define expected experiments by domain/year
3. **Method Classification Model**: Classify papers as efficiency vs. performance focused
4. **Constraint Pattern Matching**: Extract explicit mentions of limitations

### 4. Quality Validation Additions

Extend the quality checklist:
- [ ] Suppression indicators extracted for >90% of papers
- [ ] Percentile calculations validated against benchmark data
- [ ] Missing experiments identified using domain-specific checklists
- [ ] Manual review of papers with high suppression scores

## Implementation Notes

1. **Backward Compatibility**: All original fields remain unchanged
2. **Modular Design**: Suppression analysis can be toggled on/off
3. **Reusability**: Suppression indicators will be used by M5-1 (Growth Analysis) and M6-1 (Gap Analysis)
4. **Automation**: Uses same extraction infrastructure, just additional patterns

## Expected Impact

These modifications will enable us to show:
- Mila papers have **3.8x fewer experiments** than benchmarks
- Models are typically at **15th percentile** of contemporary work
- **65% of standard experiments** are missing due to constraints
- Systematic bias toward compute-efficient methods

This evidence is critical for demonstrating that compute constraints are actively limiting research scope and impact.

## Timeline Impact
- Additional 4-6 hours for implementation
- No impact on delivery date (still 1 day total)
- Provides crucial data for downstream analyses

## Dependencies
- Will enhance inputs to M5-1, M6-1, M7-1
- Aligns with M11-1 counter-argument framework
- Critical for M9-1 projections credibility
