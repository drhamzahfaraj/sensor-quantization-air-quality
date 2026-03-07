"""
train_student_distill.py
------------------------
Knowledge distillation training for the AQSC student model.

The student is distilled from the pre-trained FP32 teacher using a weighted
combination of hard cross-entropy loss and soft KL-divergence loss. This
optional step improves student accuracy by ~0.3 pp before INT8 PTQ.

Loss function:
    L = λ · CE(logits_s, y) + (1 - λ) · T² · KL(σ(z_T/T) ‖ σ(z_s/T))

Default: temperature T=4, λ=0.3 (paper §3.3)

Usage:
    python src/train_student_distill.py --config experiments/config_aqsc.yaml
"""

import argparse
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
import yaml

from models import build_model
from train_teacher import set_seed, load_split, evaluate

# ── Distillation loss ─────────────────────────────────────────────────────

class DistillationLoss(nn.Module):
    """
    Combined hard cross-entropy and soft KL-divergence loss.
    
    Args:
        temperature: Softmax temperature for soft targets (default: 4).
        alpha: Weight on hard CE loss; (1-alpha) on soft KL (default: 0.3).
    """
    
    def __init__(self, temperature: float = 4.0, alpha: float = 0.3):
        super().__init__()
        self.T = temperature
        self.alpha = alpha
    
    def forward(
        self,
        logits_s: torch.Tensor,  # student logits
        logits_t: torch.Tensor,  # teacher logits
        targets: torch.Tensor,   # ground-truth labels
    ) -> torch.Tensor:
        hard_loss = F.cross_entropy(logits_s, targets)
        soft_loss = F.kl_div(
            F.log_softmax(logits_s / self.T, dim=-1),
            F.softmax(logits_t / self.T, dim=-1),
            reduction="batchmean",
        ) * (self.T ** 2)
        return self.alpha * hard_loss + (1 - self.alpha) * soft_loss

# ── Training loop ─────────────────────────────────────────────────────

def distill_epoch(student, teacher, loader, optimiser, criterion, device):
    student.train()
    teacher.eval()
    total_loss, correct, n = 0.0, 0, 0
    with torch.no_grad():
        pass  # teacher gradients disabled during distillation
    
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimiser.zero_grad()
        logits_s = student(X_batch)
        with torch.no_grad():
            logits_t = teacher(X_batch)
        loss = criterion(logits_s, logits_t, y_batch)
        loss.backward()
        optimiser.step()
        total_loss += loss.item() * len(y_batch)
        correct += (logits_s.argmax(1) == y_batch).sum().item()
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
        train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=cfg.get("batch_size", 64), shuffle=True, num_workers=4)
        val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=cfg.get("batch_size", 64), shuffle=False, num_workers=4)
        
        # Load pre-trained teacher
        teacher = build_model(cfg.get("n_channels", 8), cfg.get("n_classes", 8)).to(device)
        teacher_ckpt = os.path.join(cfg["model_dir"], f"teacher_seed{seed}.pt")
        teacher.load_state_dict(torch.load(teacher_ckpt, map_location=device))
        teacher.eval()
        print(f"  Teacher loaded from {teacher_ckpt}")
        
        # Student: same architecture, trained from scratch
        student = build_model(cfg.get("n_channels", 8), cfg.get("n_classes", 8)).to(device)
        optimiser = torch.optim.Adam(student.parameters(), lr=cfg.get("lr", 1e-3))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimiser, T_max=cfg.get("epochs", 50))
        criterion = DistillationLoss(
            temperature=cfg.get("distill_temperature", 4.0),
            alpha=cfg.get("distill_alpha", 0.3),
        )
        val_criterion = torch.nn.CrossEntropyLoss()
        
        best_val_acc = 0.0
        for epoch in range(1, cfg.get("epochs", 50) + 1):
            train_loss, train_acc = distill_epoch(student, teacher, train_loader, optimiser, criterion, device)
            val_loss, val_acc = evaluate(student, val_loader, val_criterion, device)
            scheduler.step()
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(student.state_dict(), os.path.join(cfg["model_dir"], f"student_seed{seed}.pt"))
            
            if epoch % 10 == 0:
                print(f"  Epoch {epoch:3d} | train {train_acc:.4f} | val {val_acc:.4f} | best {best_val_acc:.4f}")
        
        results.append(best_val_acc)
        print(f"  Best val accuracy (seed {seed}): {best_val_acc:.4f}")
    
    accs = np.array(results)
    print(f"\nDistillation complete.")
    print(f"Val accuracy: {accs.mean():.4f} ± {accs.std():.4f} (n={len(seeds)} seeds)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/config_aqsc.yaml")
    args = parser.parse_args()
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    main(cfg)