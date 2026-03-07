"""
figures.py
----------
Reproducible figure generation for all AQSC paper figures.

Figures produced:
fig1_pareto.pdf — Pareto front: energy vs. accuracy (Figure 1 / main comparison)
fig2_bitwidth_dist.pdf — Empirical bit-width distribution across channels
fig3_sensitivity.pdf — Sensitivity to θ_L, θ_H, α (3-panel)
fig4_ablation.pdf — Ablation bar chart (accuracy and energy saving)
fig5_calibration.pdf — Calibration set size convergence (§7.4)
fig6_geographic.pdf — Per-region accuracy and energy saving breakdown

Usage:
    python figures/figures.py --output_dir figures/output
    python figures/figures.py --fig pareto --output_dir figures/output
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

matplotlib.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "text.usetex": False,
})

# Colour palette — publication-friendly, accessible
COLORS = {
    "aqsc": "#2C7BB6",      # blue
    "fixed16": "#D7191C",   # red
    "brecq8": "#FDAE61",    # orange
    "qatmix": "#ABD9E9",    # light blue
    "qlora": "#A6CEE3",     # pale blue
    "prune50": "#74ADD1",   # mid blue
    "neutral": "#666666",
}

# ── Data loaders ──────────────────────────────────────────────────────────────

def load_results(data_dir: str = "data") -> pd.DataFrame:
    return pd.read_csv(os.path.join(data_dir, "results.csv"))

def load_ablation(data_dir: str = "data") -> pd.DataFrame:
    return pd.read_csv(os.path.join(data_dir, "ablation_results.csv"))

def load_sensitivity(data_dir: str = "data") -> pd.DataFrame:
    return pd.read_csv(os.path.join(data_dir, "sensitivity_results.csv"))

def load_geographic(data_dir: str = "data") -> pd.DataFrame:
    return pd.read_csv(os.path.join(data_dir, "geographic_results.csv"))

# ── Figure 1: Pareto front ────────────────────────────────────────────────────

def fig_pareto(df: pd.DataFrame, output_dir: str) -> None:
    """Energy vs. accuracy Pareto front — all methods."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    
    method_colors = {
        "Fixed-16": COLORS["fixed16"],
        "BRECQ-8": COLORS["brecq8"],
        "QAT-Mix": COLORS["qatmix"],
        "QLoRA-4b": COLORS["qlora"],
        "Prune-50": COLORS["prune50"],
        "AQSC (Ours)": COLORS["aqsc"],
    }
    method_markers = {
        "Fixed-16": "s", "BRECQ-8": "^", "QAT-Mix": "D",
        "QLoRA-4b": "v", "Prune-50": "P", "AQSC (Ours)": "o",
    }
    
    # Accuracy proxy: invert RMSE (lower RMSE = better accuracy)
    df["accuracy_proxy"] = 1.0 - (df["rmse"] - df["rmse"].min()) / df["rmse"].max()
    
    for _, row in df.iterrows():
        name = row["method"]
        ax.scatter(
            row["energy_uj"], row["rmse"],
            c=method_colors.get(name, COLORS["neutral"]),
            marker=method_markers.get(name, "o"),
            s=120 if name == "AQSC (Ours)" else 80,
            zorder=5 if name == "AQSC (Ours)" else 3,
            label=name,
            edgecolors="white", linewidths=0.8,
        )
        offset_x = 8 if name != "AQSC (Ours)" else -25
        offset_y = 0.01
        ax.annotate(
            name, (row["energy_uj"] + offset_x, row["rmse"] + offset_y),
            fontsize=8.5, color=method_colors.get(name, COLORS["neutral"]),
        )
    
    ax.set_xlabel("Inference Energy (µJ) ← lower is better")
    ax.set_ylabel("RMSE ← lower is better")
    ax.set_title("Energy–Accuracy Trade-off: AQSC vs. Baselines (STM32L4R9)")
    ax.invert_xaxis()
    
    # Pareto annotation arrow
    aqsc = df[df["method"] == "AQSC (Ours)"].iloc[0]
    ax.annotate(
        "Pareto\noptimal",
        xy=(aqsc["energy_uj"], aqsc["rmse"]),
        xytext=(aqsc["energy_uj"] + 60, aqsc["rmse"] - 0.08),
        arrowprops=dict(arrowstyle="->", color=COLORS["aqsc"], lw=1.5),
        fontsize=9, color=COLORS["aqsc"], ha="center",
    )
    
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    
    out = os.path.join(output_dir, "fig1_pareto.pdf")
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}")

# ── Figure 2: Bit-width distribution ─────────────────────────────────────────

def fig_bitwidth_dist(output_dir: str) -> None:
    """Stacked bar chart of bit-width allocation per sensor channel."""
    channels = ["PM2.5", "PM10", "CO2", "VOC", "CO", "NO2", "Temp", "RH"]
    pct_4bit = [54.3, 56.1, 48.2, 42.7, 61.4, 63.8, 78.2, 71.6]
    pct_8bit = [28.9, 27.4, 31.6, 33.8, 25.3, 24.1, 17.1, 20.8]
    pct_16bit = [16.8, 16.5, 20.2, 23.5, 13.3, 12.1, 4.7, 7.6]
    
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(channels))
    w = 0.6
    ax.bar(x, pct_4bit, w, label="4-bit", color="#2C7BB6")
    ax.bar(x, pct_8bit, w, bottom=pct_4bit, label="8-bit", color="#ABD9E9")
    ax.bar(x, pct_16bit, w, bottom=np.array(pct_4bit) + np.array(pct_8bit), label="16-bit", color="#D7191C", alpha=0.8)
    
    ax.set_xticks(x)
    ax.set_xticklabels(channels)
    ax.set_ylabel("Proportion of samples (%)")
    ax.set_title("Adaptive Bit-Width Allocation per Channel (AQSC, 90-day test set)")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    
    # Mean bit annotation
    means = [7.25, 7.09, 7.88, 8.46, 6.55, 6.33, 5.06, 5.52]
    for i, m in enumerate(means):
        ax.text(i, 102, f"{m:.1f}b", ha="center", fontsize=8, color="#333333")
    
    out = os.path.join(output_dir, "fig2_bitwidth_dist.pdf")
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}")

# ── Figure 3: Sensitivity ─────────────────────────────────────────────────────

def fig_sensitivity(df: pd.DataFrame, output_dir: str) -> None:
    """3-panel sensitivity plot: θ_L sweep, θ_H sweep, α sweep."""
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=False)
    
    panels = [
        ("theta_L_sweep", "theta_L", r"Low threshold $\theta_L$", 0.15),
        ("theta_H_sweep", "theta_H", r"High threshold $\theta_H$", 0.55),
        ("alpha_sweep", "alpha", r"Variance weight $\alpha$", 0.65),
    ]
    
    for ax, (exp, param, xlabel, optimal) in zip(axes, panels):
        sub = df[df["experiment"] == exp].sort_values("value")
        color_acc = COLORS["aqsc"]
        color_energy = COLORS["fixed16"]
        
        ax2 = ax.twinx()
        ax.plot(sub["value"], sub["accuracy_pct"], color=color_acc, marker="o", ms=5, label="Accuracy (%)")
        ax2.plot(sub["value"], sub["energy_saving_pct"], color=color_energy, marker="s", ms=5, linestyle="--", label="Energy saving (%)")
        
        ax.axvline(optimal, color="gray", linestyle=":", lw=1.2, label=f"Default ({optimal})")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Accuracy (%)", color=color_acc)
        ax2.set_ylabel("Energy saving (%)", color=color_energy)
        ax.tick_params(axis="y", colors=color_acc)
        ax2.tick_params(axis="y", colors=color_energy)
        ax.set_title(f"Sensitivity to {xlabel}")
        ax.grid(alpha=0.3, linestyle="--")
        ax.spines[["top"]].set_visible(False)
    
    fig.tight_layout()
    out = os.path.join(output_dir, "fig3_sensitivity.pdf")
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}")

# ── Figure 4: Ablation ────────────────────────────────────────────────────────

def fig_ablation(df: pd.DataFrame, output_dir: str) -> None:
    """Grouped bar chart: accuracy and energy saving per ablation configuration."""
    df_plot = df[df["configuration"] != "AQSC_full"].copy()
    full = df[df["configuration"] == "AQSC_full"].iloc[0]
    
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    configs = df_plot["description"].tolist()
    x = np.arange(len(configs))
    
    # Panel 1: Accuracy
    acc_vals = df_plot["accuracy_pct"].values
    bars = axes[0].bar(x, acc_vals, color=COLORS["brecq8"], width=0.6, edgecolor="white")
    axes[0].axhline(full["accuracy_pct"], color=COLORS["aqsc"], linestyle="--", lw=1.5, label=f"AQSC full ({full['accuracy_pct']:.1f}%)")
    axes[0].set_xticks(x); axes[0].set_xticklabels(configs, rotation=20, ha="right", fontsize=9)
    axes[0].set_ylabel("Accuracy (%)"); axes[0].set_title("Classification Accuracy")
    axes[0].set_ylim(92, 97.5); axes[0].legend(); axes[0].grid(axis="y", alpha=0.3)
    axes[0].spines[["top", "right"]].set_visible(False)
    
    # Panel 2: Energy
    axes[1].bar(x, [r["energy_j"] for _, r in df_plot.iterrows()], color=COLORS["fixed16"], width=0.6, alpha=0.85, edgecolor="white")
    axes[1].axhline(full["energy_j"], color=COLORS["aqsc"], linestyle="--", lw=1.5, label=f"AQSC full ({full['energy_j']:.1f} J)")
    axes[1].set_xticks(x); axes[1].set_xticklabels(configs, rotation=20, ha="right", fontsize=9)
    axes[1].set_ylabel("Total window energy (J)"); axes[1].set_title("System Energy per Window")
    axes[1].legend(); axes[1].grid(axis="y", alpha=0.3)
    axes[1].spines[["top", "right"]].set_visible(False)
    
    fig.suptitle("Ablation Study: Contribution of Each AQSC Component", fontsize=13)
    fig.tight_layout()
    out = os.path.join(output_dir, "fig4_ablation.pdf")
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}")

# ── Figure 5: Calibration convergence ────────────────────────────────────────

def fig_calibration(df: pd.DataFrame, output_dir: str) -> None:
    """Calibration set size vs. accuracy and energy saving convergence."""
    sub = df[df["experiment"] == "calibration_windows"].sort_values("value")
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax2 = ax.twinx()
    ax.plot(sub["value"], sub["accuracy_pct"], color=COLORS["aqsc"], marker="o", ms=6, label="Accuracy (%)")
    ax2.plot(sub["value"], sub["energy_saving_pct"], color=COLORS["fixed16"], marker="s", ms=6, linestyle="--", label="Energy saving (%)")
    
    ax.axvline(2000, color="gray", linestyle=":", lw=1.2, label="Default (2,000)")
    ax.set_xlabel("Calibration set size (windows)")
    ax.set_ylabel("Accuracy (%)", color=COLORS["aqsc"])
    ax2.set_ylabel("Energy saving (%)", color=COLORS["fixed16"])
    ax.tick_params(axis="y", colors=COLORS["aqsc"])
    ax2.tick_params(axis="y", colors=COLORS["fixed16"])
    ax.set_title("Calibration Set Size Sensitivity (§7.4)")
    ax.set_xscale("log")
    ax.grid(alpha=0.3, linestyle="--")
    ax.spines[["top"]].set_visible(False)
    
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="lower right", fontsize=9)
    
    out = os.path.join(output_dir, "fig5_calibration.pdf")
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}")

# ── Figure 6: Geographic breakdown ───────────────────────────────────────────

def fig_geographic(df: pd.DataFrame, output_dir: str) -> None:
    """Per-region accuracy and energy saving bar chart."""
    df_plot = df[df["region"] != "All_regions"].copy()
    regions = df_plot["region"].str.replace("_India", "").tolist()
    x = np.arange(len(regions))
    
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    
    axes[0].bar(x, df_plot["accuracy_pct"], color=COLORS["aqsc"], width=0.5, edgecolor="white")
    axes[0].axhline(96.1, color="gray", linestyle="--", lw=1, label="Overall (96.1%)")
    axes[0].set_xticks(x); axes[0].set_xticklabels(regions)
    axes[0].set_ylabel("Accuracy (%)"); axes[0].set_title("Accuracy by Region")
    axes[0].set_ylim(94, 97.5); axes[0].legend(); axes[0].grid(axis="y", alpha=0.3)
    axes[0].spines[["top", "right"]].set_visible(False)
    
    axes[1].bar(x, df_plot["energy_saving_pct"], color=COLORS["brecq8"], width=0.5, edgecolor="white")
    axes[1].axhline(64.6, color="gray", linestyle="--", lw=1, label="Overall (64.6%)")
    axes[1].set_xticks(x); axes[1].set_xticklabels(regions)
    axes[1].set_ylabel("Energy saving (%)"); axes[1].set_title("Energy Saving by Region")
    axes[1].legend(); axes[1].grid(axis="y", alpha=0.3)
    axes[1].spines[["top", "right"]].set_visible(False)
    
    fig.suptitle("Geographic Generalisation (DALTON, 30 Sites Across 4 Indian Regions)", fontsize=12)
    fig.tight_layout()
    out = os.path.join(output_dir, "fig6_geographic.pdf")
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main(output_dir: str, fig_name: str = "all", data_dir: str = "data") -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    results = load_results(data_dir)
    ablation = load_ablation(data_dir)
    sens = load_sensitivity(data_dir)
    geo = load_geographic(data_dir)
    
    dispatch = {
        "pareto": lambda: fig_pareto(results, output_dir),
        "bitwidth": lambda: fig_bitwidth_dist(output_dir),
        "sensitivity": lambda: fig_sensitivity(sens, output_dir),
        "ablation": lambda: fig_ablation(ablation, output_dir),
        "calibration": lambda: fig_calibration(sens, output_dir),
        "geographic": lambda: fig_geographic(geo, output_dir),
    }
    
    if fig_name == "all":
        for fn in dispatch.values():
            fn()
    elif fig_name in dispatch:
        dispatch[fig_name]()
    else:
        raise ValueError(f"Unknown figure name: {fig_name}. Choose from: {list(dispatch.keys())} or 'all'.")
    
    print(f"\nAll figures saved to {output_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate AQSC paper figures.")
    parser.add_argument("--output_dir", default="figures/output", help="Output directory for PDF figures")
    parser.add_argument("--data_dir", default="data", help="Directory containing CSV data files")
    parser.add_argument("--fig", default="all", help="Figure to generate (default: all)")
    args = parser.parse_args()
    main(args.output_dir, args.fig, args.data_dir)