"""
Computational keyword database and pattern matching for resource analysis.
"""

import re
from typing import Dict

COMPUTATIONAL_INDICATORS = {
    "gpu_hardware": [
        "GPU",
        "V100",
        "A100",
        "H100",
        "RTX",
        "Tesla",
        "CUDA",
        "graphics processing unit",
        "parallel processing",
        "NVIDIA",
        "TPU",
        "tensor processing unit",
        "cloud computing",
        "distributed training",
        "GeForce",
        "Quadro",
        "Titan",
        "multi-GPU",
        "GPU cluster",
        "VRAM",
        "GPU memory",
        "CUDA cores",
        "tensor cores",
    ],
    "training_resources": [
        "training time",
        "compute hours",
        "GPU hours",
        "CPU hours",
        "wall-clock time",
        "training duration",
        "computational cost",
        "compute budget",
        "resource consumption",
        "energy consumption",
        "training cost",
        "compute time",
        "processing time",
        "runtime",
        "execution time",
        "computational overhead",
        "resource usage",
        "compute resources",
        "training resources",
    ],
    "model_scale": [
        "parameters",
        "billion parameters",
        "million parameters",
        "model size",
        "large model",
        "transformer",
        "neural network",
        "deep network",
        "architecture",
        "layers",
        "large language model",
        "LLM",
        "foundation model",
        "pre-trained model",
        "fine-tuning",
        "model weights",
        "neural architecture",
        "deep learning model",
    ],
    "dataset_scale": [
        "dataset size",
        "training data",
        "million samples",
        "billion tokens",
        "large dataset",
        "data preprocessing",
        "batch size",
        "mini-batch",
        "data loading",
        "storage requirements",
        "training samples",
        "data points",
        "training examples",
        "large-scale dataset",
        "massive dataset",
        "big data",
        "data volume",
        "training corpus",
    ],
    "optimization_compute": [
        "hyperparameter tuning",
        "grid search",
        "random search",
        "neural architecture search",
        "AutoML",
        "optimization",
        "cross-validation",
        "ablation study",
        "experimental validation",
        "hyperparameter optimization",
        "model selection",
        "parameter search",
        "optimization algorithm",
        "learning rate scheduling",
        "early stopping",
        "regularization",
    ],
    "infrastructure": [
        "cluster",
        "distributed",
        "parallel",
        "multi-gpu",
        "multi-node",
        "high performance computing",
        "HPC",
        "supercomputer",
        "cloud platform",
        "AWS",
        "Google Cloud",
        "Azure",
        "data center",
        "compute cluster",
        "distributed computing",
        "parallel computing",
        "cloud infrastructure",
        "scalable computing",
        "containerization",
        "Docker",
        "Kubernetes",
    ],
}

COMPUTATIONAL_PATTERNS = {
    "gpu_count": re.compile(
        r"(\d+)\s*(?:x\s*)?(?:GPU|V100|A100|H100|RTX|Tesla)", re.IGNORECASE
    ),
    "training_time": re.compile(
        r"(\d+(?:\.\d+)?)\s*(hours?|days?|weeks?|minutes?)", re.IGNORECASE
    ),
    "parameter_count": re.compile(
        r"(\d+(?:\.\d+)?)\s*(million|billion|M|B)\s*parameters?", re.IGNORECASE
    ),
    "dataset_size": re.compile(
        r"(\d+(?:\.\d+)?)\s*(million|billion|M|B|K)\s*(?:training\s+)?(samples?|examples?|tokens?)",
        re.IGNORECASE,
    ),
    "batch_size": re.compile(r"batch\s*size\s*(?:of\s*)?(\d+)", re.IGNORECASE),
    "memory_usage": re.compile(
        r"(\d+(?:\.\d+)?)\s*(GB|TB|MB)\s*(?:memory|RAM|VRAM)", re.IGNORECASE
    ),
    "learning_rate": re.compile(
        r"learning\s*rate\s*(?:of\s*)?(\d+(?:\.\d+)?(?:e-?\d+)?)", re.IGNORECASE
    ),
    "epochs": re.compile(r"(\d+)\s*epochs?", re.IGNORECASE),
    "compute_cost": re.compile(
        r"\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:in\s*)?compute", re.IGNORECASE
    ),
    "flops": re.compile(r"(\d+(?:\.\d+)?)\s*(T|G|M)?FLOPS?", re.IGNORECASE),
}


def get_total_keyword_count() -> int:
    """Get total number of keywords across all categories"""
    return sum(len(keywords) for keywords in COMPUTATIONAL_INDICATORS.values())


def get_category_counts() -> Dict[str, int]:
    """Get keyword count for each category"""
    return {
        category: len(keywords)
        for category, keywords in COMPUTATIONAL_INDICATORS.items()
    }


def validate_patterns() -> Dict[str, bool]:
    """Validate regex patterns by testing with sample text"""
    test_cases = {
        "gpu_count": "We used 8 GPUs for training",
        "training_time": "Training took 24 hours",
        "parameter_count": "The model has 175 billion parameters",
        "dataset_size": "Dataset contains 1.2 million samples",
        "batch_size": "batch size of 32",
        "memory_usage": "Required 16 GB VRAM",
        "learning_rate": "learning rate 0.001",
        "epochs": "trained for 100 epochs",
        "compute_cost": "$50,000 in compute costs",
        "flops": "2.3 TFLOPS",
    }

    results = {}
    for pattern_name, test_text in test_cases.items():
        pattern = COMPUTATIONAL_PATTERNS[pattern_name]
        matches = pattern.findall(test_text)
        results[pattern_name] = len(matches) > 0

        # Additional validation for group counts
        if matches:
            expected_groups = {
                "gpu_count": 1,
                "training_time": 2,
                "parameter_count": 2,
                "dataset_size": 3,
                "batch_size": 1,
                "memory_usage": 2,
                "learning_rate": 1,
                "epochs": 1,
                "compute_cost": 1,
                "flops": 2,
            }

            actual_groups = len(matches[0]) if isinstance(matches[0], tuple) else 1
            expected = expected_groups.get(pattern_name, 1)

            if actual_groups != expected:
                results[f"{pattern_name}_group_count_error"] = (
                    f"Expected {expected} groups, got {actual_groups}"
                )

    return results
