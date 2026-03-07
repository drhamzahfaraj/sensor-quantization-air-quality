"""
preprocess_unep.py
------------------
Data loading and preprocessing for the DALTON Indoor Air Quality dataset
and OpenAQ/UNEP supplementary calibration data.

Outputs:
    data/processed/train.npz — training windows + labels
    data/processed/val.npz — validation windows + labels
    data/processed/test.npz — test windows + labels
    data/processed/calibration.npz — first 2,000 windows for AQSC calibration

Usage:
    python src/preprocess_unep.py --data_dir data/raw --output_dir data/processed
"""

import argparse
import os
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Dict

# ── Constants ────────────────────────────────────────────────────────────────

CHANNELS = ["pm25", "pm10", "co2", "voc", "co", "no2", "temperature", "humidity"]
ACTIVITY_CLASSES = {
    "cooking": 0,
    "cleaning": 1,
    "sleeping": 2,
    "ventilation": 3,
    "idle": 4,
    "electronic": 5,
    "eating": 6,
    "other": 7,
}
WINDOW_SIZE = 600       # 10 minutes at 1 Hz
STRIDE = 60             # 1-minute stride for windowing
CALIBRATION_N = 2_000   # number of calibration windows (see §7.4 of paper)

# Temporal split (month indices 1–6)
TRAIN_MONTHS = [1, 2, 3]
VAL_MONTHS = [4]
TEST_MONTHS = [5, 6]

# ── Loading ──────────────────────────────────────────────────────────────────

def load_site_csv(filepath: str) -> pd.DataFrame:
    """Load a single DALTON site CSV into a DataFrame with standardised columns."""
    df = pd.read_csv(filepath, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    # Rename columns to canonical names
    rename_map = {
        "PM2.5": "pm25", "PM10": "pm10", "CO2": "co2",
        "VOC": "voc", "CO": "co", "NO2": "no2",
        "Temp": "temperature", "RH": "humidity",
        "label": "activity"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df[["timestamp"] + CHANNELS + ["activity"]]

def load_all_sites(data_dir: str) -> pd.DataFrame:
    """Load and concatenate data from all DALTON site CSVs."""
    data_dir = Path(data_dir)
    site_files = sorted(data_dir.glob("site_*.csv"))
    if not site_files:
        raise FileNotFoundError(f"No site CSV files found in {data_dir}")
    frames = [load_site_csv(str(f)) for f in site_files]
    df = pd.concat(frames, ignore_index=True)
    print(f"Loaded {len(site_files)} sites — {len(df):,} total samples")
    return df

# ── Preprocessing ─────────────────────────────────────────────────────────────

def remove_outliers(df: pd.DataFrame, clip_sigma: float = 5.0) -> pd.DataFrame:
    """Clip sensor values beyond clip_sigma standard deviations per channel."""
    for ch in CHANNELS:
        mu, sigma = df[ch].mean(), df[ch].std()
        df[ch] = df[ch].clip(mu - clip_sigma * sigma, mu + clip_sigma * sigma)
    return df

def interpolate_missing(df: pd.DataFrame, max_gap_s: int = 60) -> pd.DataFrame:
    """Linear interpolation for gaps up to max_gap_s seconds; NaN fill otherwise."""
    df = df.set_index("timestamp").sort_index()
    df = df.resample("1S").interpolate(method="linear", limit=max_gap_s)
    df = df.fillna(method="ffill", limit=5).fillna(0.0)
    return df.reset_index()

def normalise(df: pd.DataFrame) -> Tuple[pd.DataFrame, MinMaxScaler]:
    """Min-max normalise all sensor channels to [0, 1] using training set statistics."""
    scaler = MinMaxScaler()
    df[CHANNELS] = scaler.fit_transform(df[CHANNELS])
    return df, scaler

# ── Windowing ────────────────────────────────────────────────────────────────

def sliding_windows(
    df: pd.DataFrame,
    window_size: int = WINDOW_SIZE,
    stride: int = STRIDE,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract overlapping sliding windows from a time-series DataFrame.
    
    Returns:
        X: float32 array of shape (N, window_size, n_channels)
        y: int64 array of shape (N,) — majority-vote label per window
    """
    data = df[CHANNELS].values.astype(np.float32)
    labels = df["activity"].values
    X, y = [], []
    for start in range(0, len(data) - window_size + 1, stride):
        end = start + window_size
        X.append(data[start:end])
        # Majority vote over window for activity label
        window_labels = labels[start:end]
        unique, counts = np.unique(window_labels[window_labels >= 0], return_counts=True)
        majority = unique[counts.argmax()] if len(unique) > 0 else 7
        y.append(majority)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)

# ── Split ───────────────────────────────────────────────────────────────────

def month_split(
    df: pd.DataFrame,
    train_months: list = TRAIN_MONTHS,
    val_months: list = VAL_MONTHS,
    test_months: list = TEST_MONTHS,
) -> Dict[str, pd.DataFrame]:
    """Temporal split by month index to prevent future leakage."""
    df["month"] = pd.to_datetime(df["timestamp"]).dt.month
    first_month = df["month"].min()
    df["month_idx"] = df["month"] - first_month + 1
    return {
        "train": df[df["month_idx"].isin(train_months)].copy(),
        "val": df[df["month_idx"].isin(val_months)].copy(),
        "test": df[df["month_idx"].isin(test_months)].copy(),
    }

# ── Main ────────────────────────────────────────────────────────────────────

def preprocess(data_dir: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    
    print("Loading DALTON site data...")
    df = load_all_sites(data_dir)
    
    print("Cleaning and interpolating...")
    df = remove_outliers(df)
    df = interpolate_missing(df)
    
    print("Splitting by month...")
    splits = month_split(df)
    
    # Fit scaler on training data only
    _, scaler = normalise(splits["train"])
    for split_name, split_df in splits.items():
        split_df[CHANNELS] = scaler.transform(split_df[CHANNELS])
        splits[split_name] = split_df
    
    for split_name, split_df in splits.items():
        print(f"Windowing {split_name} split ({len(split_df):,} samples)...")
        X, y = sliding_windows(split_df)
        out_path = os.path.join(output_dir, f"{split_name}.npz")
        np.savez_compressed(out_path, X=X, y=y)
        print(f"  → {out_path}: X={X.shape}, y={y.shape}")
    
    # Calibration set: first CALIBRATION_N windows of training data
    X_train, y_train = sliding_windows(splits["train"])
    X_cal = X_train[:CALIBRATION_N]
    y_cal = y_train[:CALIBRATION_N]
    cal_path = os.path.join(output_dir, "calibration.npz")
    np.savez_compressed(cal_path, X=X_cal, y=y_cal)
    print(f"Calibration set saved: {cal_path} (n={CALIBRATION_N} windows)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preprocess DALTON data for AQSC.")
    parser.add_argument("--data_dir", default="data/raw", help="Raw site CSV directory")
    parser.add_argument("--output_dir", default="data/processed", help="Output directory for .npz files")
    args = parser.parse_args()
    preprocess(args.data_dir, args.output_dir)