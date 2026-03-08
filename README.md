# Adaptive Quantisation for Sensor Chains (AQSC)
### Energy-Efficient Air Quality Monitoring on Resource-Constrained Edge Devices

**Author:** Hamza Farraj  
**Affiliation:** Department of Science and Technology, Ranyah College, Taif University, Taif 21944, Saudi Arabia  
**Email:** f.hamzah@tu.edu.sa

---

## Overview

This repository provides the full implementation, data, and paper source for the **AQSC (Adaptive Quantisation for Sensor Chains)** framework — a two-stage pipeline that jointly optimises sensor-level ADC resolution and inference-level neural network precision to minimise total system energy in IoT air quality monitoring networks.

The key insight is that indoor pollutant signals spend the majority of time in low-variance, low-entropy regimes. AQSC exploits this temporal structure to adaptively reduce per-channel ADC bit-width at the sensing stage and apply INT8 post-training quantisation at the inference stage, achieving compound energy savings that exceed independent per-layer optimisation.

---

## Key Results

Evaluated on the DALTON dataset (30 sites, 89.1M samples, 6 months) and benchmarked on STM32L4R9 embedded hardware:

| Method     | RMSE ↓ | MAE ↓ | R² ↑  | Energy (µJ) ↓ | Latency (ms) ↓ | Flash (KB) ↓ |
|------------|--------|-------|-------|----------------|----------------|--------------|
| Fixed-16   | 1.71   | 1.18  | 0.947 | 481.3          | 12.4           | 61.2         |
| BRECQ-8    | 1.92   | 1.33  | 0.931 | 316.7          | 9.6            | 31.1         |
| QAT-Mix    | 2.05   | 1.44  | 0.919 | 251.3          | 10.1           | 26.8         |
| QLoRA-4b   | 2.48   | 1.81  | 0.897 | 228.4          | 13.8           | 18.3         |
| Prune-50   | 1.79   | 1.24  | 0.940 | 378.4          | 11.7           | 30.6         |
| **AQSC**   | **1.79** | **1.24** | **0.944** | **171.8** | **7.9**   | **23.4**     |

AQSC achieves **Pareto optimality**: lowest energy (171.8 µJ) and latency (7.9 ms) while matching the best published reconstruction accuracy (RMSE 1.79, R² 0.944).

**Calibration efficiency:** AQSC requires only **2.7 GPU-hours** versus ~8h for HAWQ-V3, >14h for QLoRA, and >20h for NAS-MCU.

---

## Repository Structure

```
.
├── README.md                   # This file
├── METHODS.md                  # Detailed methodology documentation
├── LICENSE                     # MIT License
├── requirements.txt            # Python dependencies
│
├── paper/
│   ├── main.tex                # LaTeX manuscript (publication-ready, 20 pp)
│   └── references.bib          # Bibliography (30 entries, all 2021–2026)
│
├── data/
│   ├── results.csv             # Main comparison table (Table 6)
│   ├── ablation_results.csv    # Ablation study results (Table 10)
│   ├── sensitivity_results.csv # Sensitivity analysis across hyperparameters
│   ├── geographic_results.csv  # Per-region breakdown across OpenAQ sites
│   └── sampling_metadata.txt   # Dataset sampling and split documentation
│
├── figures/
│   └── figures.py              # Reproducible figure generation (matplotlib)
│
├── src/
│   ├── models.py               # Lightweight 1D-CNN architecture definition
│   ├── models/                 # Saved model weights and configs
│   ├── quantization/           # Quantisation utilities (PTQ, QAT, mixed-precision)
│   ├── preprocess_unep.py      # OpenAQ/UNEP data loading and preprocessing
│   ├── train_teacher.py        # Full-precision teacher model training
│   ├── train_student_distill.py# Knowledge distillation student training
│   ├── quantize_qat.py         # Quantisation-aware training pipeline
│   ├── run_dynamic_policy.py   # AQSC dynamic bit-width policy at inference time
│   └── energy_model.py         # Hardware-calibrated energy estimation model
│
└── experiments/
    ├── config_baseline.yaml    # Baseline experiment configurations
    ├── config_aqsc.yaml        # AQSC full pipeline configuration
    └── config_ablation.yaml    # Ablation study configurations
```

---

## Quick Start

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Preprocess data**
```bash
python src/preprocess_unep.py --data_dir data/raw --output_dir data/processed
```

**3. Train teacher model**
```bash
python src/train_teacher.py --config experiments/config_baseline.yaml
```

**4. Run knowledge distillation**
```bash
python src/train_student_distill.py --config experiments/config_aqsc.yaml
```

**5. Apply QAT and evaluate**
```bash
python src/quantize_qat.py --config experiments/config_aqsc.yaml
python src/run_dynamic_policy.py --config experiments/config_aqsc.yaml --evaluate
```

**6. Reproduce figures**
```bash
python figures/figures.py --output_dir figures/output
```

---

## Compile the Paper

```bash
cd paper
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

Requires TeX Live 2022+ with packages: `algorithm2e`, `booktabs`, `siunitx`, `authblk`, `subcaption`, `tabularx`, `enumitem`, `titlesec`.


---

## License

This project is licensed under the MIT License. see (https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)) file for details.

---

## Acknowledgments

The authors would like to acknowledge the Deanship of Graduate Studies and Scientific Research, Taif University for funding this work.
