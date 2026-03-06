# Optimizing Sensor Quantisation for Energy Saving in Air Quality Monitoring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LaTeX](https://img.shields.io/badge/LaTeX-Paper-blue.svg)](paper/main.tex)

## Overview

This repository contains the LaTeX source and supporting materials for the research paper:

> **Optimizing Sensor Quantisation for Energy Saving in Air Quality Monitoring**
>
> *Hamza Farraj*
> Department of Computer Science, King Abdulaziz University, Jeddah, Saudi Arabia

## Abstract

This paper proposes a **Variance-Aware Adaptive Bit-Width Quantisation (VABQ)** framework that jointly optimises sensor-level ADC resolution and inference-level post-training quantisation (PTQ) to minimise energy consumption in IoT-based air quality monitoring while preserving monitoring fidelity.

### Key Results
- **61.3%** reduction in sensor-level ADC energy consumption
- **74.8%** reduction in inference energy
- **64.6%** total system energy saving
- Classification accuracy maintained above **96.1%**
- Signal reconstruction NRMSE below **2.4%**

## Methodology: VABQ Framework

The framework operates in two cascaded stages:

### Stage 1: Variance-Aware Sensor Quantisation
- Rolling variance computation over 10-minute sliding windows
- Shannon entropy estimation for information-theoretic content
- Variance-entropy criterion dynamically selects between **4-bit**, **8-bit**, and **16-bit** ADC resolution
- Exploits the periodic structure of indoor air quality signals

### Stage 2: Inference-Level Post-Training Quantisation
- Lightweight 1D-CNN (~45K parameters) for pollutant event classification
- INT8 post-training quantisation using min-max calibration
- Deployable within ESP32's 520 KB SRAM

## Dataset

**DALTON** — Indoor air quality dataset from IIT Kharagpur:
- 28 deployment sites (households, apartments, labs, canteens, classrooms)
- 3 months of continuous monitoring
- 8 sensor channels: PM₂.₅, PM₁₀, CO₂, VOC, CO, NO₂, Temperature, Humidity
- 1 Hz sampling rate, 42 occupants with annotated activities
- ESP32-based sensor nodes (ESP-WROOM-32)

## Repository Structure

```
├── paper/
│   ├── main.tex              # Main LaTeX document
│   ├── references.bib        # Bibliography
│   └── sections/
│       ├── abstract.tex       # Abstract
│       ├── sec1_introduction.tex
│       ├── sec2_related_work.tex
│       ├── sec3_methodology.tex
│       ├── sec4_experiments.tex
│       ├── sec5_results.tex
│       ├── sec6_discussion.tex
│       └── sec7_conclusion.tex
├── README.md
└── .gitignore
```

## Building the Paper

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Or using `latexmk`:
```bash
cd paper
latexmk -pdf main.tex
```

## Citation

If you use this work, please cite:

```bibtex
@article{farraj2026vabq,
  title={Optimizing Sensor Quantisation for Energy Saving in Air Quality Monitoring},
  author={Farraj, Hamza},
  year={2026}
}
```

## Keywords

Sensor quantisation · Energy efficiency · Air quality monitoring · Adaptive bit-width · Post-training quantisation · Edge AI · Internet of Things · DALTON

## License

This project is licensed under the MIT License.
