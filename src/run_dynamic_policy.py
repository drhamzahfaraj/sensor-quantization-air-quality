"""
run_dynamic_policy.py
---------------------
AQSC dynamic bit-width policy: runs the Stage A sensor quantisation policy
at inference time and evaluates end-to-end accuracy and energy consumption.

The policy computes rolling variance and entropy per channel, assigns
bit-widths via the composite criterion Γ_c(t), and feeds quantised windows
into the INT8 inference model.

Usage:
    # Evaluate on test set and report accuracy + energy
    python src/run_dynamic_policy.py --config experiments/config_aqsc.yaml --evaluate
    
    # Run on a single window (streaming mode)
    python src/run_dynamic_policy.py --config experiments/config_aqsc.yaml --stream
"""

import argparse
import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from collections import deque
import yaml

from models import build_model
from train_teacher import set_seed, load_split
from energy_model import AQSCEnergyModel

# ── Variance-Entropy Criterion ────────────────────────────────────────────

class VarianceEntropyController:
    """
    Per-channel adaptive bit-width controller implementing the AQSC Stage A policy.
    
    Maintains rolling variance and entropy for each sensor channel and maps
    the composite criterion Γ_c(t) to a 3-tier bit-width allocation (4, 8, 16).
    
    Args:
        n_channels: Number of sensor channels (default: 8).
        window_size: Rolling window length in samples (default: 600).
        alpha: Variance weight in composite criterion (default: 0.65).
        theta_low: Lower threshold for 4-bit/8-bit boundary (default: 0.15).
        theta_high: Upper threshold for 8-bit/16-bit boundary (default: 0.55).
        n_bins: Number of histogram bins for entropy estimation (default: 16).
    """
    
    BIT_WIDTHS = [4, 8, 16]
    
    def __init__(
        self,
        n_channels: int = 8,
        window_size: int = 600,
        alpha: float = 0.65,
        theta_low: float = 0.15,
        theta_high: float = 0.55,
        n_bins: int = 16,
    ):
        self.n_channels = n_channels
        self.window_size = window_size
        self.alpha = alpha
        self.theta_low = theta_low
        self.theta_high = theta_high
        self.n_bins = n_bins
        
        # Welford running statistics per channel
        self._count = np.zeros(n_channels)
        self._mean = np.zeros(n_channels)
        self._M2 = np.zeros(n_channels)
        
        # Circular buffer for entropy estimation
        self._buffer = [deque(maxlen=window_size) for _ in range(n_channels)]
        
        # Calibration maxima (set during calibration)
        self.sigma2_max = np.ones(n_channels)
        self.H_max = np.ones(n_channels)
    
    def calibrate(self, X_cal: np.ndarray) -> None:
        """
        Compute per-channel σ²_max and H_max from calibration windows.
        
        Args:
            X_cal: float32 array of shape (N_windows, window_size, n_channels)
        """
        all_variance = np.var(X_cal.reshape(-1, self.n_channels), axis=0)
        self.sigma2_max = np.maximum(all_variance, 1e-8)
        
        all_entropy = np.zeros((X_cal.shape[0], self.n_channels))
        for w in range(X_cal.shape[0]):
            for c in range(self.n_channels):
                counts, _ = np.histogram(X_cal[w, :, c], bins=self.n_bins, range=(0.0, 1.0))
                probs = counts / counts.sum()
                probs = probs[probs > 0]
                all_entropy[w, c] = -np.sum(probs * np.log2(probs))
        self.H_max = np.maximum(all_entropy.max(axis=0), 1e-8)
        print(f"Calibration complete. σ²_max={self.sigma2_max.round(4)}, H_max={self.H_max.round(4)}")
    
    def _welford_update(self, x: np.ndarray) -> np.ndarray:
        """Online Welford update; returns current per-channel variance."""
        self._count += 1
        delta = x - self._mean
        self._mean += delta / self._count
        delta2 = x - self._mean
        self._M2 += delta * delta2
        count = np.maximum(self._count, 2)
        return self._M2 / count
    
    def _entropy(self, channel_idx: int) -> float:
        buf = np.array(self._buffer[channel_idx])
        if len(buf) < 2:
            return 0.0
        counts, _ = np.histogram(buf, bins=self.n_bins, range=(0.0, 1.0))
        probs = counts / counts.sum()
        probs = probs[probs > 0]
        return -np.sum(probs * np.log2(probs))
    
    def assign_bits(self, sample: np.ndarray) -> np.ndarray:
        """
        Assign bit-width for each channel given a single new sample.
        
        Args:
            sample: float32 array of shape (n_channels,)
        
        Returns:
            bits: int array of shape (n_channels,) with values in {4, 8, 16}
        """
        for c in range(self.n_channels):
            self._buffer[c].append(float(sample[c]))
        
        variance = self._welford_update(sample)
        H = np.array([self._entropy(c) for c in range(self.n_channels)])
        
        gamma = (
            self.alpha * variance / self.sigma2_max
            + (1 - self.alpha) * H / self.H_max
        )
        gamma = np.clip(gamma, 0.0, 1.0)
        
        bits = np.where(gamma < self.theta_low, 4,
                        np.where(gamma < self.theta_high, 8, 16))
        return bits
    
    def quantise_sample(self, sample: np.ndarray, bits: np.ndarray) -> np.ndarray:
        """Simulate bit-width reduction by rounding to b-bit precision."""
        quantised = sample.copy()
        for c in range(self.n_channels):
            b = int(bits[c])
            levels = 2 ** b - 1
            quantised[c] = np.round(sample[c] * levels) / levels
        return quantised

# ── Evaluation ────────────────────────────────────────────────────────────

@torch.no_grad()
def evaluate_dynamic(
    model: nn.Module,
    controller: VarianceEntropyController,
    energy_model: AQSCEnergyModel,
    X_test: np.ndarray,
    y_test: np.ndarray,
    device: torch.device,
) -> dict:
    """
    Evaluate AQSC end-to-end: apply dynamic bit-width policy, then run inference.
    
    Returns dict with accuracy, mean_bits, energy_saving_pct.
    """
    model.eval()
    correct, total = 0, 0
    bit_history = []
    energy_total = 0.0
    
    n_windows = X_test.shape[0]
    X_quantised = np.zeros_like(X_test)
    
    for w in range(n_windows):
        window = X_test[w]  # (600, 8)
        window_bits = np.zeros_like(window, dtype=int)
        
        for t in range(window.shape[0]):
            bits = controller.assign_bits(window[t])
            window_bits[t] = bits
            X_quantised[w, t] = controller.quantise_sample(window[t], bits)
        
        bit_history.append(window_bits.mean())
        energy_total += energy_model.window_energy(window_bits)
    
    # Batch inference on quantised windows
    X_tensor = torch.tensor(X_quantised, dtype=torch.float32)
    y_tensor = torch.tensor(y_test, dtype=torch.long)
    loader = DataLoader(TensorDataset(X_tensor, y_tensor), batch_size=256, shuffle=False)
    
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        logits = model(X_batch)
        correct += (logits.argmax(1) == y_batch).sum().item()
        total += len(y_batch)
    
    baseline_energy = energy_model.baseline_energy(n_windows)
    mean_bits = float(np.mean(bit_history))
    
    return {
        "accuracy": correct / total,
        "mean_bits": mean_bits,
        "energy_uj": energy_total * 1e6,
        "baseline_energy_uj": baseline_energy * 1e6,
        "energy_saving_pct": (1 - energy_total / baseline_energy) * 100,
        "n_windows": n_windows,
    }

# ── Main ────────────────────────────────────────────────────────────────────

def main(cfg: dict, mode: str) -> None:
    device = torch.device("cpu")
    seed = cfg.get("seeds", [42])[0]
    set_seed(seed)
    
    # Load model
    model = build_model(cfg.get("n_channels", 8), cfg.get("n_classes", 8)).to(device)
    ckpt = os.path.join(cfg["model_dir"], f"student_seed{seed}.pt")
    model.load_state_dict(torch.load(ckpt, map_location=device))
    model.eval()
    print(f"Loaded model: {ckpt}")
    
    # Load calibration data and calibrate controller
    X_cal, _ = load_split(cfg["data_dir"], "calibration")
    controller = VarianceEntropyController(
        n_channels=cfg.get("n_channels", 8),
        window_size=cfg.get("window_size", 600),
        alpha=cfg.get("alpha", 0.65),
        theta_low=cfg.get("theta_low", 0.15),
        theta_high=cfg.get("theta_high", 0.55),
    )
    controller.calibrate(X_cal.numpy())
    
    energy_model = AQSCEnergyModel(n_channels=cfg.get("n_channels", 8))
    
    if mode == "evaluate":
        X_test, y_test = load_split(cfg["data_dir"], "test")
        print(f"\nEvaluating on test set ({len(X_test):,} windows)...")
        results = evaluate_dynamic(model, controller, energy_model, X_test.numpy(), y_test.numpy(), device)
        
        print(f"\n── AQSC Results ──────────────────────────────")
        print(f"  Accuracy: {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
        print(f"  Mean bit-width: {results['mean_bits']:.2f} bits (baseline: 16)")
        print(f"  Inference energy: {results['energy_uj']:.1f} µJ")
        print(f"  Baseline energy: {results['baseline_energy_uj']:.1f} µJ")
        print(f"  Energy saving: {results['energy_saving_pct']:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/config_aqsc.yaml")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()
    
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    
    mode = "evaluate" if args.evaluate else "stream"
    main(cfg, mode)