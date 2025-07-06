# Domain Classification Analysis - Key Findings

## Executive Summary

Analysis of 2,786 Mila papers (2019-2024) reveals significant discrepancies between research domain classification and dataset/environment-based classification, with major implications for computational resource projections.

## Core Data

- **Total papers**: 2,786 (1,444 with research domain analysis, 881 with datasets/environments)
- **Analysis coverage**: 52% of papers have extractable research domains
- **Dataset/environment coverage**: 61% of analyzed papers mention specific data sources

## Original Research Domain Distribution

1. **Computer Vision & Medical Imaging**: 874 papers (21.9%)
2. **Natural Language Processing**: 803 papers (20.2%)
3. **Reinforcement Learning & Robotics**: 747 papers (18.8%)
4. **Deep Learning & Neural Architectures**: 746 papers (18.7%)
5. **Graph Learning & Network Analysis**: 317 papers (8.0%)
6. **Software Engineering & Systems**: 166 papers (4.2%)
7. **Machine Learning Theory & Methods**: 162 papers (4.1%)

## Dataset-Only Classification Results

1. **Computer Vision & Medical Imaging**: 327 papers (37.1%)
2. **Natural Language Processing**: 267 papers (30.3%)
3. **Graph Learning & Network Analysis**: 99 papers (11.2%)
4. **Reinforcement Learning & Robotics**: 67 papers (7.6%)
5. **Scientific Computing & Applications**: 44 papers (5.0%)

## Enhanced Classification (Datasets + Environments)

**Critical RL Improvement:**
- **Dataset-only RL**: 67 papers (2.9%)
- **Enhanced RL**: 190 papers (8.3%)
- **Improvement**: +123 papers (+183.6%)

## Agreement Analysis

**Domain-Specific Agreement Rates:**
- **CV**: 45.6% agreement, 64.8% dataset precision, 60.6% research precision
- **NLP**: 39.7% agreement, 63.7% dataset precision, 51.4% research precision
- **RL**: 21.0% agreement, 91.0% dataset precision, 21.5% research precision
- **Graph**: 25.7% agreement, 57.6% dataset precision, 31.7% research precision

**Overall**: 59.7% agreement rate between methods

## Multi-Domain Reality

- **89.4% of papers are interdisciplinary** (multiple domains)
- **Average 3.18 domains per paper**
- **Deep Learning appears in 52.3%** of papers as enabling technology

## Correction Factors

**Research domains appear to:**
- **Underestimate CV by 1.7x** (should be ~30-40% not 22%)
- **Underestimate NLP by 1.5x** (should be ~30% not 20%)
- **Overestimate RL by 2.3x** (should be ~8% not 19%)

## Key Biases Identified

**Dataset/Environment Method Biases:**
- CV/NLP have standard datasets (ImageNet, GLUE) → easier detection
- RL uses environments → missed without enhanced analysis
- Theory papers lack datasets → underrepresented

**Research Domain Method Biases:**
- Overly inclusive (3.18 domains/paper)
- May include theoretical work without computational requirements
- Better captures interdisciplinary nature

## Final Corrected Estimates (Multi-Domain + Dataset Evidence)

1. **Computer Vision & Medical Imaging**: 29.4% (375 papers)
2. **Natural Language Processing**: 28.2% (359 papers)
3. **Graph Learning & Network Analysis**: 17.5% (223 papers)
4. **Scientific Computing & Applications**: 17.2% (219 papers)
5. **Reinforcement Learning & Robotics**: 7.7% (98 papers)

## Computational Implications

**For 2025-2027 Resource Planning:**
- **CV + NLP dominate**: 57.6% of computational workload
- **GPU-intensive**: CV requires high GPU memory/compute
- **Memory-intensive**: NLP requires large-scale model training
- **RL computational work**: ~8-10% realistic estimate (not 19%)

## Methodology Recommendations

**For computational projections:**
1. **Use enhanced method** (datasets + environments)
2. **Weight toward dataset evidence** (70% datasets, 30% research domains)
3. **Account for multi-domain reality** (papers span multiple areas)
4. **Focus on experimental papers** (those with datasets/environments)

## Critical Questions Resolved

1. **"Are we missing RL papers?"** → YES, environments matter (+183% improvement)
2. **"Should we correct based on datasets?"** → YES, but with enhancements for RL
3. **"Are research domains reliable?"** → Partially, but overcount theoretical work
4. **"What's the true distribution?"** → CV ~30%, NLP ~28%, RL ~8%, Graph ~18%