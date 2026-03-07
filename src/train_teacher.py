"""
train_teacher.py
----------------
Full-precision (FP32) teacher model training for AQSC.

The teacher is an identical AQSC_CNN architecture trained with standard
cross-entropy loss. Its soft labels are later used for knowledge distillation
in train_student_distill.py.

Usage:
    python src/train_teacher.py --config experiments/config_baseline.yaml
"""

import argparse
import os
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import yaml

from models import build_model

# ── Reproducibility ───────────────────────────────────────────────────────

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

# ── Data loading ──────────────────────────────────────────────────────────

def load_split(data_dir: str, split: str):
    path = os.path.join(data_dir, f"{split}.npz")
    data = np.load(path)
    X = torch.tensor(data["X"], dtype=torch.float32)
    y = torch.tensor(data["y"], dtype=torch.long)
    return X, y

# ── Training loop ───────────────────────────────────────────────────────

def train_epoch(model, loader, optimiser, criterion, device):
    model.train()
    total_loss, correct, n = 0.0, 0, 0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimiser.zero_grad()
        logits = model(X_batch)
        loss = criterion(logits, y_batch)
        loss.backward()
        optimiser.step()
        total_loss += loss.item() * len(y_batch)
        correct += (logits.argmax(1) == y_batch).sum().item()
        n += len(y_batch)
    return total_loss / n, correct / n

@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, n = 0.0, 0, 0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        logits = model(X_batch)
        loss = criterion(logits, y_batch)
        total_loss += loss.item() * len(y_batch)
        correct += (logits.argmax(1) == y_batch).sum().item()
        n += len(y_batch)
    return total_loss / n, correct / n

# ── Main ────────────────────────────────────────────────────────────────────

def main(cfg: dict) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    seeds = cfg.get("seeds", [42, 43, 44, 45, 46])
    results = []
    
    for seed in seeds:
        print(f"\n── Seed {seed} ──────────────────────────────")
        set_seed(seed)
        
        X_train, y_train = load_split(cfg["data_dir"], "train")
        X_val, y_val = load_split(cfg["data_dir"], "val")
        
        train_loader = DataLoader(
            TensorDataset(X_train, y_train),
            batch_size=cfg.get("batch_size", 64), shuffle=True, num_workers=4
        )
        val_loader = DataLoader(
            TensorDataset(X_val, y_val),
            batch_size=cfg.get("batch_size", 64), shuffle=False, num_workers=4
        )
        
        model = build_model(
            n_channels=cfg.get("n_channels", 8),
            n_classes=cfg.get("n_classes", 8)
        ).to(device)
        
        optimiser = torch.optim.Adam(model.parameters(), lr=cfg.get("lr", 1e-3))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimiser, T_max=cfg.get("epochs", 50)
        )
        criterion = nn.CrossEntropyLoss()
        
        best_val_acc = 0.0
        for epoch in range(1, cfg.get("epochs", 50) + 1):
            train_loss, train_acc = train_epoch(model, train_loader, optimiser, criterion, device)
            val_loss, val_acc = evaluate(model, val_loader, criterion, device)
            scheduler.step()
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                os.makedirs(cfg["model_dir"], exist_ok=True)
                torch.save(model.state_dict(), os.path.join(cfg["model_dir"], f"teacher_seed{seed}.pt"))
            
            if epoch % 10 == 0:
                print(f"  Epoch {epoch:3d} | train {train_acc:.4f} | val {val_acc:.4f} | best {best_val_acc:.4f}")
        
        results.append(best_val_acc)
        print(f"  Best val accuracy (seed {seed}): {best_val_acc:.4f}")
    
    accs = np.array(results)
    print(f"\nTeacher training complete.")
    print(f"Val accuracy: {accs.mean():.4f} ± {accs.std():.4f} (n={len(seeds)} seeds)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/config_baseline.yaml")
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    main(cfg)