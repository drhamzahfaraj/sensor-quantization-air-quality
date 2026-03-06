# Optimizing Sensor Quantisation for Energy Saving in Air Quality Monitoring

**Author:** Hamza Farraj  
**Affiliation:** Department of Computer Science, King Abdulaziz University, Jeddah, Saudi Arabia

## Overview

This repository contains the LaTeX source for a research paper proposing the **Variance-Aware Adaptive Bit-Width Quantisation (VABQ)** framework. VABQ jointly optimises sensor-level ADC resolution and inference-level post-training quantisation (PTQ) to minimise total system energy in IoT air quality monitoring networks.

## Key Results

| Metric | Value |
|--------|-------|
| Total system energy saving | **64.6%** |
| Sensor-level ADC energy saving | 61.3% |
| Inference energy saving (INT8 PTQ) | 74.8% |
| Classification accuracy (8-class) | 96.1% |
| Signal reconstruction NRMSE | < 2.4% |
| Mean adaptive bit-width | 6.77 bits (vs 16-bit baseline) |

## Paper Structure

```
paper/
├── main.tex                    # Master document
├── references.bib              # 40 citations (2020-2026, 34 from 2023+)
└── sections/
    ├── abstract.tex            # Abstract + keywords
    ├── sec1_introduction.tex   # Motivation, problem, contributions, organisation
    ├── sec2_related_work.tex   # 6 subsections + research gap table
    ├── sec3_methodology.tex    # System overview, Stage 1, Stage 2, unified objective
    ├── sec4_experiments.tex    # Dataset, partitioning, baselines, metrics, implementation
    ├── sec5_results.tex        # 7 subsections with 6 tables
    ├── sec6_discussion.tex     # Practical, generalisability, NAS, novelty, limitations
    └── sec7_conclusion.tex     # Summary and future work
```

## Dataset

**DALTON** — Indoor Air Quality Dataset with Activities of Daily Living  
- 30 indoor sites, 4 geographic regions, 46 occupants  
- 6 months (summer + winter), 1 Hz sampling  
- 8 channels: PM₂.₅, PM₁₀, CO₂, VOC, CO, NO₂, temperature, humidity  
- [Karmakar et al., NeurIPS 2024 Datasets Track](https://arxiv.org/abs/2407.14501)

## Build

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Citation Count Verification

40 unique BibTeX entries in `references.bib`, all cited in the manuscript:
- 2025-2026: 14 citations
- 2023-2024: 20 citations  
- 2020-2022: 6 citations (foundational works)

## License

This work is provided for academic purposes.
